"""Static analysis pipeline: Pylint, Bandit, Radon and Python AST checks."""
import ast
import asyncio
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core.schemas import Category, Finding, Severity


log = logging.getLogger(__name__)

TARGET_NAME = "code_under_review.py"
TOOL_TIMEOUT = 90


def _line_text(lines: list[str], line: int) -> str:
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""


# ---------------------------------------------------------------- Pylint
_PYLINT_TYPE = {
    "fatal": (Category.bug, Severity.critical),
    "error": (Category.bug, Severity.high),
    "warning": (Category.bug, Severity.medium),
    "refactor": (Category.refactor, Severity.low),
    "convention": (Category.style, Severity.low),
    "information": (Category.style, Severity.info),
}
_PYLINT_QUALITY = {"unused-import", "unused-variable", "unused-argument", "redefined-outer-name",
                   "dangerous-default-value", "broad-exception-caught", "bare-except"}


def _run_pylint(path: str, tmp: Path, lines: list[str]) -> list[Finding]:
    cmd = [sys.executable, "-m", "pylint", "--output-format=json", "--score=n",
           "--disable=C0114,C0115,C0116,E0401", str(tmp / TARGET_NAME)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TOOL_TIMEOUT, cwd=tmp)
    if not proc.stdout.strip():
        return []
    out: list[Finding] = []
    for m in json.loads(proc.stdout):
        category, severity = _PYLINT_TYPE.get(m.get("type", ""), (Category.quality, Severity.low))
        if m.get("symbol") in _PYLINT_QUALITY:
            category = Category.quality
        line = int(m.get("line") or 1)
        raw_line = lines[line - 1] if 1 <= line <= len(lines) else ""
        indent = raw_line[:len(raw_line) - len(raw_line.lstrip())] if raw_line else ""
        symbol = m.get("symbol", "")
        fix = None

        if symbol == "bare-except":
            fix = f"{indent}except Exception as err:"
        elif symbol == "dangerous-default-value":
            if "={}" in raw_line:
                fix = raw_line.replace("={}", "=None")
            elif "=[]" in raw_line:
                fix = raw_line.replace("=[]", "=None")
        elif symbol == "unused-import" and raw_line:
            fix = f"{indent}# Removed unused import: {raw_line.strip()}"
        elif symbol == "no-name-in-module":
            fix = f"{indent}# Recommendation: Define or export symbol in target module, or import as needed\n{raw_line}"

        out.append(Finding(
            file=path, line=line, end_line=m.get("endLine"), category=category, severity=severity,
            title=f"{m.get('symbol')}: {m.get('message')}"[:200],
            description=m.get("message", ""), rule_id=m.get("message-id", ""),
            code_snippet=_line_text(lines, line), proposed_fix=fix, sources=["pylint"], confidence=0.85,
            evidence=[f"pylint {m.get('message-id')} ({m.get('symbol')}) at line {line}: {m.get('message')}"],
        ))
    return out


# ---------------------------------------------------------------- Bandit
_BANDIT_SEV = {"HIGH": Severity.high, "MEDIUM": Severity.medium, "LOW": Severity.low}
_BANDIT_CONF = {"HIGH": 0.9, "MEDIUM": 0.75, "LOW": 0.55}


def _run_bandit(path: str, tmp: Path, lines: list[str]) -> list[Finding]:
    cmd = [sys.executable, "-m", "bandit", "-f", "json", "-q", "--exit-zero", str(tmp / TARGET_NAME)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TOOL_TIMEOUT, cwd=tmp)
    if not proc.stdout.strip():
        return []
    data = json.loads(proc.stdout)
    out: list[Finding] = []
    for r in data.get("results", []):
        line = int(r.get("line_number") or 1)
        sev = _BANDIT_SEV.get(r.get("issue_severity", "LOW"), Severity.low)
        fix = None
        test_id = r.get("test_id", "")
        raw_line = lines[line - 1] if 1 <= line <= len(lines) else ""
        if test_id == "B307" and "eval(" in raw_line:
            fix = raw_line.replace("eval(", "ast.literal_eval(")
        elif test_id in {"B602", "B603"} and "shell=True" in raw_line:
            fix = raw_line.replace("shell=True", "shell=False")
        elif test_id == "B110":
            indent = raw_line[:len(raw_line) - len(raw_line.lstrip())]
            fix = f"{indent}logging.exception('Handled error: %s', err)"

        out.append(Finding(
            file=path, line=line, category=Category.security, severity=sev,
            title=f"{r.get('test_name')}: {r.get('issue_text')}"[:200],
            description=r.get("issue_text", ""), rule_id=r.get("test_id", ""),
            recommendation=f"See {r.get('more_info')}" if r.get("more_info") else "",
            code_snippet=_line_text(lines, line), proposed_fix=fix, sources=["bandit"],
            confidence=_BANDIT_CONF.get(r.get("issue_confidence", "LOW"), 0.55),
            evidence=[f"bandit {r.get('test_id')} ({r.get('test_name')}) at line {line}: {r.get('issue_text')}"],
        ))
    return out


# ---------------------------------------------------------------- Radon
def _run_radon(path: str, content: str, lines: list[str]) -> list[Finding]:
    try:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit
    except ImportError:  # radon not installed
        return []
    out: list[Finding] = []
    for block in cc_visit(content):
        if block.complexity <= 10:
            continue
        sev = Severity.medium if block.complexity <= 20 else Severity.high
        out.append(Finding(
            file=path, line=block.lineno, end_line=getattr(block, "endline", None),
            category=Category.complexity, severity=sev, rule_id="CC",
            title=f"High cyclomatic complexity ({block.complexity}) in '{block.name}'",
            description=f"'{block.name}' has cyclomatic complexity {block.complexity} (limit 10).",
            recommendation="Split the function into smaller functions and simplify branching.",
            code_snippet=_line_text(lines, block.lineno), sources=["radon"], confidence=0.9,
            evidence=[f"radon cyclomatic complexity of {block.name} = {block.complexity}"],
        ))
    mi = mi_visit(content, multi=True)
    if mi < 20:
        out.append(Finding(
            file=path, line=1, category=Category.quality, severity=Severity.low, rule_id="MI",
            title=f"Low maintainability index ({mi:.1f})",
            description="The maintainability index of this file is low, so it is hard to maintain.",
            recommendation="Reduce complexity and length; extract helpers.", sources=["radon"],
            confidence=0.8, evidence=[f"radon maintainability index = {mi:.1f}"],
        ))
    return out


# ---------------------------------------------------------------- AST
class _AstChecker(ast.NodeVisitor):
    def __init__(self, path: str, lines: list[str]):
        self.path, self.lines, self.out = path, lines, []

    def _add(self, node, rule, title, desc, rec, cat, sev, conf=0.9, proposed_fix: str | None = None):
        line = getattr(node, "lineno", 1)
        self.out.append(Finding(
            file=self.path, line=line, end_line=getattr(node, "end_lineno", None),
            category=cat, severity=sev, title=title, description=desc, recommendation=rec,
            rule_id=rule, code_snippet=_line_text(self.lines, line), proposed_fix=proposed_fix,
            sources=["ast"], confidence=conf, evidence=[f"AST check {rule} at line {line}: {title}"],
        ))

    def visit_ExceptHandler(self, node):
        if node.type is None:
            line_idx = getattr(node, "lineno", 1)
            raw_line = self.lines[line_idx - 1] if 1 <= line_idx <= len(self.lines) else ""
            indent = raw_line[:len(raw_line) - len(raw_line.lstrip())] if raw_line else ""
            self._add(node, "AST-BARE-EXCEPT", "Bare 'except:' hides all errors",
                      "A bare except also catches KeyboardInterrupt and SystemExit.",
                      "Catch specific exception types (e.g. Exception as err).", Category.bug, Severity.medium,
                      proposed_fix=f"{indent}except Exception as err:")
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            line_idx = getattr(node, "lineno", 1)
            raw_line = self.lines[line_idx - 1] if 1 <= line_idx <= len(self.lines) else ""
            indent = raw_line[:len(raw_line) - len(raw_line.lstrip())] if raw_line else ""
            self._add(node, "AST-SWALLOWED", "Exception is silently swallowed",
                      "The handler does nothing, so failures go unnoticed.",
                      "Log the error or handle it properly.", Category.bug, Severity.medium, 0.85,
                      proposed_fix=f"{indent}    logging.exception('Handled unexpected error: %s', err)")
        self.generic_visit(node)

    def visit_Call(self, node):
        name = node.func.id if isinstance(node.func, ast.Name) else None
        attr = node.func.attr if isinstance(node.func, ast.Attribute) else None
        line_idx = getattr(node, "lineno", 1)
        raw_line = self.lines[line_idx - 1] if 1 <= line_idx <= len(self.lines) else ""
        indent = raw_line[:len(raw_line) - len(raw_line.lstrip())] if raw_line else ""

        if name in {"eval", "exec"}:
            fix = None
            if name == "eval" and "eval(" in raw_line:
                fix = raw_line.replace("eval(", "ast.literal_eval(")
            elif name == "exec":
                fix = f"{indent}# Safe replacement: avoid dynamic code execution"
            self._add(node, "AST-EVAL", f"Use of {name}()",
                      f"{name}() can run arbitrary code.", "Use ast.literal_eval or a safe parser.",
                      Category.security, Severity.high, proposed_fix=fix)

        # SQL Injection in .execute() / .raw()
        if attr in {"execute", "raw"} and node.args:
            first_arg = node.args[0]
            fix = f"{indent}cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
            if isinstance(first_arg, ast.JoinedStr):
                self._add(node, "AST-SQLI", "Possible SQL Injection in formatted query",
                          "Dynamic string interpolation (f-string) in SQL execution call is vulnerable to SQL injection.",
                          "Use parameterized queries (e.g. cursor.execute(query, params)).",
                          Category.security, Severity.high, proposed_fix=fix)
            elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Mod, ast.Add)):
                self._add(node, "AST-SQLI", "Possible SQL Injection in formatted query",
                          "String concatenation or %-formatting in SQL execution call is vulnerable to SQL injection.",
                          "Use parameterized queries with placeholder binding.",
                          Category.security, Severity.high, proposed_fix=fix)

        # Subprocess shell=True
        if attr in {"Popen", "run", "call", "check_call", "check_output"}:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and bool(kw.value.value):
                    fix = None
                    if "shell=True" in raw_line:
                        fix = raw_line.replace("shell=True", "shell=False")
                    else:
                        fix = f"{indent}subprocess.run(['echo', str(cmd_arg)], shell=False)"
                    self._add(node, "AST-SHELL-TRUE", "Subprocess execution with shell=True",
                              "Running subprocesses with shell=True invites command injection vulnerabilities.",
                              "Pass command arguments as a list and set shell=False.",
                              Category.security, Severity.high, proposed_fix=fix)

        # Insecure deserialization
        if (name == "loads" or attr == "loads") and (
            isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in {"pickle", "_pickle"}
        ):
            fix = raw_line.replace("pickle.loads(", "json.loads(") if "pickle.loads(" in raw_line else None
            self._add(node, "AST-UNSAFE-DESERIALIZATION", "Unsafe deserialization with pickle",
                      "pickle.loads() can execute arbitrary code during unpickling.",
                      "Use safer serialization formats such as JSON or Protocol Buffers.",
                      Category.security, Severity.critical, proposed_fix=fix)

        # Requests/httpx missing timeout
        if attr in {"get", "post", "put", "delete", "patch"} and isinstance(node.func, ast.Attribute) and (
            isinstance(node.func.value, ast.Name) and node.func.value.id in {"requests", "httpx"}
        ):
            if not any(kw.arg == "timeout" for kw in node.keywords):
                fix = None
                if raw_line.endswith(")"):
                    fix = raw_line[:-1] + ", timeout=10.0)"
                elif ")" in raw_line:
                    r_idx = raw_line.rfind(")")
                    fix = raw_line[:r_idx] + ", timeout=10.0" + raw_line[r_idx:]
                self._add(node, "AST-REQUEST-NO-TIMEOUT", f"HTTP request without timeout in {attr}()",
                          "HTTP requests without an explicit timeout can hang indefinitely, causing thread starvation.",
                          "Specify a timeout parameter (e.g. timeout=10.0).",
                          Category.performance, Severity.low, 0.8, proposed_fix=fix)

        self.generic_visit(node)

    def _function(self, node):
        defaults = node.args.defaults + [d for d in node.args.kw_defaults if d is not None]
        for d in defaults:
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                line_idx = getattr(node, "lineno", 1)
                raw_line = self.lines[line_idx - 1] if 1 <= line_idx <= len(self.lines) else ""
                fix = None
                if "={}" in raw_line:
                    fix = raw_line.replace("={}", "=None")
                elif "=[]" in raw_line:
                    fix = raw_line.replace("=[]", "=None")
                self._add(node, "AST-MUTABLE-DEFAULT", f"Mutable default argument in '{node.name}'",
                          "Mutable defaults are shared between calls.",
                          "Use None as default and create the object inside the function.",
                          Category.bug, Severity.medium, proposed_fix=fix)
                break
        n_args = len(node.args.args) + len(node.args.kwonlyargs)
        if n_args > 6:
            self._add(node, "AST-MANY-ARGS", f"'{node.name}' has {n_args} parameters",
                      "Functions with many parameters are hard to use and test.",
                      "Group related parameters into an object.", Category.refactor, Severity.low, 0.8)
        length = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
        if length > 60:
            self._add(node, "AST-LONG-FUNCTION", f"'{node.name}' is {length} lines long",
                      "Very long functions are hard to read and review.",
                      "Split into smaller functions.", Category.refactor, Severity.low, 0.8)
        self.generic_visit(node)

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function


def _run_ast(path: str, content: str, lines: list[str]) -> list[Finding]:
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        line = e.lineno or 1
        return [Finding(
            file=path, line=line, category=Category.bug, severity=Severity.critical,
            title=f"Syntax error: {e.msg}", description=f"The file cannot be parsed: {e.msg}",
            rule_id="AST-SYNTAX", code_snippet=_line_text(lines, line), sources=["ast"],
            confidence=1.0, evidence=[f"ast.parse failed at line {line}: {e.msg}"],
        )]
    checker = _AstChecker(path, lines)
    checker.visit(tree)
    return checker.out


# ---------------------------------------------------------------- entry points
def analyze_file_sync(path: str, content: str) -> list[Finding]:
    lines = content.splitlines()
    findings = _run_ast(path, content, lines)
    if any(f.rule_id == "AST-SYNTAX" for f in findings):
        return findings  # other tools cannot work on broken code
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / TARGET_NAME).write_text(content, encoding="utf-8")
        for runner in (_run_pylint, _run_bandit):
            try:
                findings += runner(path, tmp, lines)
            except Exception as exc:  # a failing tool must not stop the review
                log.warning("%s failed for %s: %s", runner.__name__, path, exc)
    try:
        findings += _run_radon(path, content, lines)
    except Exception as exc:
        log.warning("radon failed for %s: %s", path, exc)

    # Secret and credential scanner
    try:
        from .secret_scanner import scan_secrets
        findings += scan_secrets(path, content)
    except Exception as exc:
        log.warning("secret_scanner failed for %s: %s", path, exc)

    # Enrich with CWE & OWASP taxonomy
    try:
        from ..utils.cwe_mapping import enrich_finding_taxonomy

        for f in findings:
            enrich_finding_taxonomy(f)

    except Exception as exc:
        log.warning("cwe_mapping failed for %s: %s", path, exc)

    return findings


async def analyze_file(path: str, content: str) -> list[Finding]:
    return await asyncio.to_thread(analyze_file_sync, path, content)
