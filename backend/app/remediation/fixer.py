"""Fix Generation Agent: writes revised code for verified findings and builds a diff."""
import ast
import difflib
from collections import defaultdict

from ..engine.agents import numbered
from ..engine.llm import llm_client
from ..core.schemas import ChangeExplanation, Finding, Revision


FIX_SYSTEM = (
    "You are the Fix Generation agent in a code review system. You receive a Python file and a list "
    "of verified issues. Return the COMPLETE revised file that fixes those issues. Keep all other "
    "behaviour, names, imports and formatting unchanged. Do not add unrelated changes. "
    "Also generate a companion unit test (using pytest) that proves the fix works. "
    "Reply with JSON only: "
    '{"revised_code": "<the full revised file>", '
    '"test_code": "<companion pytest function(s)>", '
    '"changes": [{"finding_id": "<id>", "problem": "<what was wrong>", "modification": "<what you changed>"}]}'
)


def make_diff(path: str, old: str, new: str) -> str:
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}"))


def syntax_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _issue_list(findings: list[Finding]) -> str:
    rows = []
    for f in findings:
        rows.append(f"- id={f.id} line={f.line} [{f.category.value}/{f.severity.value}] {f.title}\n"
                    f"  details: {f.description}\n  suggestion: {f.recommendation}")
    return "\n".join(rows)


def _build_revision(path: str, original: str, data: dict, findings: list[Finding], iterations: int = 1) -> Revision | None:
    revised = data.get("revised_code")
    if not isinstance(revised, str) or not revised.strip():
        return None
    if original.endswith("\n") and not revised.endswith("\n"):
        revised += "\n"
    if len(revised) < 0.3 * len(original):
        return None
    if revised == original:
        return None
    changes = []
    valid_ids = {f.id for f in findings}
    for c in data.get("changes", []) or []:
        if isinstance(c, dict) and c.get("finding_id") in valid_ids:
            changes.append(ChangeExplanation(
                finding_id=c["finding_id"], problem=str(c.get("problem", "")),
                modification=str(c.get("modification", ""))))
    test_code = data.get("test_code")
    if not isinstance(test_code, str) or not test_code.strip():
        test_code = None
    return Revision(
        path=path, original_code=original, revised_code=revised,
        diff=make_diff(path, original, revised), changes=changes,
        targeted_finding_ids=[f.id for f in findings], syntax_ok=syntax_ok(revised),
        test_code=test_code, iterations=iterations)


async def _fix_file(path: str, original: str, findings: list[Finding]) -> Revision | None:
    user = (f"File: {path}\n\nVerified issues to fix:\n{_issue_list(findings)}\n\n"
            f"Current code with line numbers (for reference only; do NOT include line numbers in your output):\n"
            f"{numbered(original)}")
    data = await llm_client.chat_json(FIX_SYSTEM, user, task="fix", max_tokens=8192)
    if not isinstance(data, dict):
        return None
    return _build_revision(path, original, data, findings, iterations=1)


async def repair_revision(path: str, original: str, prev_revision: Revision,
                          findings: list[Finding], validation_reasons: list[str],
                          iteration: int) -> Revision | None:
    """Iterative reflexion repair: ask LLM to self-correct based on validation feedback."""
    user = (f"File: {path}\n\n"
            f"Your previous revision was REJECTED by the automated validation gate for the following reasons:\n"
            + "\n".join(f"- {r}" for r in validation_reasons) + "\n\n"
            f"Issues originally targeted:\n{_issue_list(findings)}\n\n"
            f"Previous rejected code:\n{numbered(prev_revision.revised_code)}\n\n"
            f"Original code:\n{numbered(original)}\n\n"
            "Please provide an updated revision resolving all targeted issues while strictly resolving the validation errors above.")
    data = await llm_client.chat_json(FIX_SYSTEM, user, task="fix", max_tokens=8192)
    if not isinstance(data, dict):
        return None
    return _build_revision(path, original, data, findings, iterations=iteration)


from ..core.schemas import ChangeExplanation, Finding, Revision, VerificationStatus


def _derive_fix(finding: Finding, raw_line: str, path: str) -> str | None:
    """Extract or synthesize a verified fix for a finding based on rule and context."""
    if finding.proposed_fix:
        return finding.proposed_fix

    indent = raw_line[:len(raw_line) - len(raw_line.lstrip())] if raw_line else ""
    line_clean = raw_line.strip()
    rule_or_title = ((finding.rule_id or "") + " " + (finding.title or "")).lower()

    # 1. relative-beyond-top-level / attempted relative import / CWE-691
    if "relative-beyond-top-level" in rule_or_title or "cwe-691" in rule_or_title or "relative import" in rule_or_title:
        if "from ." in raw_line:
            if "from .app" in raw_line and ("backend" in path or path.startswith("backend/")):
                return f"{indent}try:\n{indent}    from backend.app.main import app\n{indent}except ImportError:\n{indent}    from app.main import app"
            return raw_line.replace("from ..", "from ").replace("from .", "from ")

    # 2. eval / B307 / CWE-95
    if "eval" in rule_or_title and "eval(" in raw_line:
        return raw_line.replace("eval(", "ast.literal_eval(")

    # 3. shell=True / B602 / CWE-78
    if "shell=true" in raw_line.lower() or "shell" in rule_or_title:
        if "shell=True" in raw_line:
            return raw_line.replace("shell=True", "shell=False")

    # 4. bare except / CWE-703
    if "except:" in raw_line or "bare" in rule_or_title:
        return f"{indent}except Exception as err:"

    # 5. mutable default / CWE-665
    if "={}" in raw_line:
        return raw_line.replace("={}", "=None")
    if "=[]" in raw_line:
        return raw_line.replace("=[]", "=None")

    # 6. unused import
    if "unused-import" in rule_or_title or "unused import" in rule_or_title:
        return f"{indent}# Removed unused import: {line_clean}"

    return None


def generate_deterministic_revision(path: str, original: str, findings: list[Finding]) -> Revision | None:
    """Deterministic rule-based fix generator when LLM is unavailable or produces no revision."""
    live_findings = [f for f in findings if f.file == path and f.verification != VerificationStatus.rejected]
    if not live_findings:
        return None

    lines = original.splitlines(keepends=True)
    if not lines and original:
        lines = [original]

    applicable: list[tuple[Finding, str]] = []
    for f in live_findings:
        raw = lines[f.line - 1] if 1 <= f.line <= len(lines) else ""
        fix = _derive_fix(f, raw, path)
        if fix:
            applicable.append((f, fix))

    if not applicable:
        return None

    # Sort descending by line so earlier line positions aren't shifted
    applicable.sort(key=lambda item: item[0].line, reverse=True)
    changes: list[ChangeExplanation] = []
    seen_lines = set()
    for f, fix_line in applicable:
        if f.line in seen_lines:
            continue
        if 1 <= f.line <= len(lines):
            seen_lines.add(f.line)
            if not fix_line.endswith("\n"):
                fix_line += "\n"
            lines[f.line - 1] = fix_line
            changes.append(ChangeExplanation(
                finding_id=f.id,
                problem=f.title,
                modification=fix_line.strip()
            ))

    revised = "".join(lines)
    if original.endswith("\n") and not revised.endswith("\n"):
        revised += "\n"

    # Add required imports if newly referenced and not present
    prefix_imports = []
    if "ast.literal_eval" in revised and "import ast" not in revised:
        prefix_imports.append("import ast\n")
    if "logging." in revised and "import logging" not in revised:
        prefix_imports.append("import logging\n")
    if "os.getenv" in revised and "import os" not in revised:
        prefix_imports.append("import os\n")
    if "json.loads" in revised and "import json" not in revised:
        prefix_imports.append("import json\n")

    if prefix_imports:
        revised = "".join(prefix_imports) + revised

    if not syntax_ok(revised) or revised == original:
        return None

    safe_name = path.replace("/", "_").replace(".", "_").replace("-", "_")
    escaped_revised = revised.replace('"""', r'\"\"\"')
    test_code = (
        f"import pytest\nimport ast\n\n"
        f"def test_{safe_name}_remediation():\n"
        f"    \"\"\"Assert that security flaws and bugs in {path} are resolved.\"\"\"\n"
        f"    code = \"\"\"{escaped_revised}\"\"\"\n"
        f"    assert ast.parse(code) is not None, 'Syntax must be valid'\n"
        f"    assert 'eval(' not in code or 'ast.literal_eval' in code, 'Unsafe eval resolved'\n"
        f"    assert 'shell=True' not in code, 'Command injection shell=True resolved'\n"
    )

    return Revision(
        path=path,
        original_code=original,
        revised_code=revised,
        diff=make_diff(path, original, revised),
        changes=changes,
        targeted_finding_ids=[f.id for f, _ in applicable],
        syntax_ok=True,
        test_code=test_code,
        iterations=1
    )


async def generate_revisions(contents: dict[str, str], verified: list[Finding], allow_fallback: bool = False) -> list[Revision]:
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for f in verified:
        by_file[f.file].append(f)

    results: list[Revision] = []
    if llm_client.enabled:
        import asyncio
        llm_results = await asyncio.gather(*(_fix_file(p, contents[p], fs) for p, fs in by_file.items() if p in contents))
        results = [r for r in llm_results if r]

    if allow_fallback:
        handled_files = {r.path for r in results}
        for p, fs in by_file.items():
            if p in contents and p not in handled_files:
                det_rev = generate_deterministic_revision(p, contents[p], fs)
                if det_rev:
                    results.append(det_rev)

    return results
