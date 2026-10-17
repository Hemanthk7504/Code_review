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


async def generate_revisions(contents: dict[str, str], verified: list[Finding]) -> list[Revision]:
    if not llm_client.enabled:
        return []
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for f in verified:
        by_file[f.file].append(f)
    import asyncio
    results = await asyncio.gather(*(_fix_file(p, contents[p], fs) for p, fs in by_file.items() if p in contents))
    return [r for r in results if r]
