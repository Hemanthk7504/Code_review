"""Evidence-Based Verification Engine.

Performs deep syntactic and AST-context verification to corroborate real vulnerabilities
and refute false positives (e.g. safe parameterized SQL queries, safe literal_eval,
shell=False argument lists, dummy test fixtures/placeholders, and sanitized inputs).
"""
import ast
import math
import os
import re
from typing import Tuple

from ..core.schemas import Category, Finding, VerificationStatus


def _calc_entropy(data: str) -> float:
    if not data:
        return 0.0
    entropy = 0.0
    for x in set(data):
        p_x = float(data.count(x)) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy


def _extract_surrounding_code(lines: list[str], line_no: int, radius: int = 5) -> str:
    start = max(0, line_no - radius - 1)
    end = min(len(lines), line_no + radius)
    return "\n".join(lines[start:end])


# -----------------------------------------------------------------------------
# PYTHON AST EVIDENCE EVALUATOR
# -----------------------------------------------------------------------------
class PythonEvidenceVisitor(ast.NodeVisitor):
    def __init__(self, target_line: int, cwe_or_rule: str):
        self.target_line = target_line
        self.cwe_or_rule = (cwe_or_rule or "").lower()
        self.verdict = "unsure"
        self.reason = ""
        self.confidence = 0.5

    def visit_Call(self, node: ast.Call):
        call_line = getattr(node, "lineno", 0)
        # Check calls within 2 lines of reported defect
        if abs(call_line - self.target_line) <= 2:
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            # 1. SQL Injection Checks (CWE-89)
            if "89" in self.cwe_or_rule or "sql" in self.cwe_or_rule or func_name in {"execute", "executemany", "raw"}:
                # If call is cursor.execute(query, params) or similar with 2+ arguments
                if len(node.args) >= 2 or any(kw.arg in {"params", "parameters", "args"} for kw in node.keywords):
                    self.verdict = "refuted"
                    self.reason = "Query uses safe parameterized binding (separate query and parameter arguments)."
                    self.confidence = 0.98
                    return
                # If first arg is a single literal string without formatting or modulo
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    query_str = node.args[0].value
                    if "{" not in query_str and "%s" not in query_str:
                        self.verdict = "refuted"
                        self.reason = "Query string is a static constant literal without dynamic user string interpolation."
                        self.confidence = 0.95
                        return
                # If query is an unescaped JoinedStr (f-string) with no parameter binding
                if node.args and isinstance(node.args[0], ast.JoinedStr):
                    self.verdict = "confirmed"
                    self.reason = "Unescaped Python f-string directly interpolated into SQL query statement."
                    self.confidence = 0.96
                    return
                # If query uses % or .format()
                if node.args and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Mod):
                    self.verdict = "confirmed"
                    self.reason = "SQL query constructed via string modulo formatting (%) rather than parameterized markers."
                    self.confidence = 0.95
                    return

            # 2. Command Injection Checks (CWE-78)
            if "78" in self.cwe_or_rule or "command" in self.cwe_or_rule or func_name in {"run", "Popen", "call", "check_call", "check_output", "system"}:
                shell_kw = next((kw for kw in node.keywords if kw.arg == "shell"), None)
                has_shell_true = shell_kw and isinstance(shell_kw.value, ast.Constant) and shell_kw.value.value is True

                # If shell=False (or omitted in subprocess.run) and first arg is list
                if not has_shell_true:
                    if node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
                        self.verdict = "refuted"
                        self.reason = "Subprocess invoked with argument vector list and shell=False (immune to shell metacharacter injection)."
                        self.confidence = 0.98
                        return

                if has_shell_true:
                    if node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                        self.verdict = "confirmed"
                        self.reason = "Dynamic string formatting executed inside shell=True subshell."
                        self.confidence = 0.98
                        return
                    if node.args and isinstance(node.args[0], ast.Constant):
                        self.verdict = "refuted"
                        self.reason = "Fixed constant command executed in shell without user interpolation."
                        self.confidence = 0.90
                        return

            # 3. Eval / Code Execution (CWE-95)
            if "95" in self.cwe_or_rule or "eval" in self.cwe_or_rule:
                if isinstance(node.func, ast.Attribute) and node.func.attr == "literal_eval":
                    self.verdict = "refuted"
                    self.reason = "ast.literal_eval is safely restricted to Python literals (cannot execute arbitrary code)."
                    self.confidence = 0.99
                    return
                if func_name == "eval" and node.args and isinstance(node.args[0], ast.Constant):
                    self.verdict = "refuted"
                    self.reason = "Static constant expression passed to eval()."
                    self.confidence = 0.90
                    return
                if func_name == "eval":
                    self.verdict = "confirmed"
                    self.reason = "Unsafe eval() of dynamic expression detected."
                    self.confidence = 0.95
                    return

        self.generic_visit(node)


def verify_evidence(f: Finding, content: str) -> Tuple[str, str, float]:
    """Verify code evidence for a finding.

    Returns:
        (verdict, reason, confidence) where verdict is 'confirmed', 'refuted', or 'unsure'.
    """
    lines = content.splitlines()
    if f.line < 1 or f.line > max(1, len(lines)):
        return ("refuted", f"Reported line {f.line} is out of bounds for file with {len(lines)} lines.", 1.0)

    target_line_text = lines[f.line - 1].strip()
    cwe_or_rule = f"{f.cwe_id or ''} {f.rule_id or ''} {f.title or ''}".lower()
    surrounding = _extract_surrounding_code(lines, f.line, radius=4)

    # -------------------------------------------------------------------------
    # 1. Hardcoded Secret / Key Validation (CWE-798)
    # -------------------------------------------------------------------------
    if "798" in cwe_or_rule or "secret" in cwe_or_rule or "credential" in cwe_or_rule or "api-key" in cwe_or_rule:
        path_lower = f.file.lower()
        is_test = any(t in path_lower for t in ["test", "mock", "fixture", "spec", "fake", "sample"])
        line_lower = target_line_text.lower()

        # Dummy / placeholder keywords
        placeholder_indicators = [
            "dummy", "example", "placeholder", "fake", "your_key", "sample",
            "test_secret", "xxxx", "00000", "123456", "changeme", "todo"
        ]
        if any(p in line_lower for p in placeholder_indicators) or is_test:
            return ("refuted", f"Matched credential is in a test fixture/mock or is a known placeholder ('{target_line_text[:40]}...').", 0.96)

        # Environment variable fallback
        if "os.getenv(" in target_line_text or "process.env." in target_line_text or "System.getenv(" in target_line_text:
            return ("refuted", "Credential is read from an environment variable.", 0.95)

        # Entropy measurement on matched candidate
        candidate_strings = re.findall(r'["\']([a-zA-Z0-9_\-\.\/+=]{8,})["\']', target_line_text)
        if candidate_strings:
            max_entropy = max(_calc_entropy(s) for s in candidate_strings)
            if max_entropy < 3.2:
                return ("refuted", f"String has low Shannon entropy ({max_entropy:.2f} < 3.2 bits); standard text, not a secret.", 0.92)
            else:
                return ("confirmed", f"Verified high-entropy credential ({max_entropy:.2f} bits) in production code context.", 0.96)

    # -------------------------------------------------------------------------
    # 2. Python-Specific AST Verification & Bandit Filter
    # -------------------------------------------------------------------------
    if "b404" in cwe_or_rule:
        if "shell=true" not in content.lower():
            return ("refuted", "Import of subprocess with safe invocations (no shell=True) is informational, not a defect.", 0.96)

    if "b101" in cwe_or_rule:
        path_lower = f.file.lower()
        if any(t in path_lower for t in ["test", "mock", "spec", "fixture"]):
            return ("refuted", "Use of assert in test file is standard pytest assertion, not a defect.", 0.98)

    if "b603" in cwe_or_rule or "b607" in cwe_or_rule:
        if "shell=true" not in surrounding.lower():
            return ("refuted", "Subprocess invoked without shell=True is immune to shell metacharacter injection.", 0.96)

    if f.file.endswith(".py"):
        try:
            tree = ast.parse(content)
            visitor = PythonEvidenceVisitor(f.line, cwe_or_rule)
            visitor.visit(tree)
            if visitor.verdict != "unsure":
                return (visitor.verdict, visitor.reason, visitor.confidence)
        except SyntaxError:
            pass

        # Check relative import protected by try/except ImportError
        if "relative-beyond-top-level" in cwe_or_rule or "cwe-691" in cwe_or_rule:
            if "try:" in surrounding and "except ImportError" in surrounding:
                return ("refuted", "Relative import is safely wrapped in a try/except ImportError fallback.", 0.98)

    # -------------------------------------------------------------------------
    # 3. JavaScript / TypeScript Specific Evidence
    # -------------------------------------------------------------------------
    if any(f.file.endswith(ext) for ext in [".js", ".jsx", ".ts", ".tsx"]):
        if "unhandled-promise" in cwe_or_rule:
            if "return" in surrounding or "await" in surrounding:
                return ("refuted", "Async function properly awaits/returns promise; error propagation to caller is standard JavaScript practice.", 0.95)
        # Prototype pollution check: safe if Object.create(null) or Map
        if "1321" in cwe_or_rule or "prototype" in cwe_or_rule:
            if "Object.create(null)" in surrounding or "new Map(" in surrounding:
                return ("refuted", "Object uses Object.create(null) or Map; immune to prototype pollution.", 0.95)
        # DOM XSS: check if sanitized with DOMPurify
        if "79" in cwe_or_rule or "xss" in cwe_or_rule:
            if "DOMPurify.sanitize" in surrounding or "sanitizeHtml" in surrounding:
                return ("refuted", "Markup assignment is sanitized with DOMPurify.", 0.95)
        # Child process: check if execFile or spawn with array
        if "78" in cwe_or_rule or "command" in cwe_or_rule:
            if ("execFile(" in target_line_text or "spawn(" in target_line_text) and "[" in target_line_text:
                return ("refuted", "Command executed via execFile/spawn with argument array (shell: false).", 0.95)

    # -------------------------------------------------------------------------
    # 4. Go & Java SQL Parameterized Checks
    # -------------------------------------------------------------------------
    if any(f.file.endswith(ext) for ext in [".go", ".java"]):
        if "89" in cwe_or_rule or "sql" in cwe_or_rule:
            if "?" in target_line_text or "$1" in target_line_text:
                if "," in target_line_text:
                    return ("refuted", "Query uses parameterized markers (?, $1) with separate argument binding.", 0.95)

    return ("unsure", "Code evidence is inconclusive through static rules alone.", 0.5)
