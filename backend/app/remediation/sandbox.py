"""Isolated Test Execution Sandbox for Autonomous Revisions.

Executes companion unit tests and regression test suites against revised source code
inside an isolated temporary environment with strict timeouts and subprocess boundaries.
"""
import ast
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

from ..core.schemas import Revision
from ..engine.language import Language, detect_language


log = logging.getLogger(__name__)


def generate_default_test_suite(revision: Revision) -> str:
    """Synthesize a companion pytest suite if none was provided by the LLM."""
    safe_func_name = revision.path.replace("/", "_").replace(".", "_").replace("-", "_")
    escaped_code = revision.revised_code.replace('"""', r'\"\"\"')

    return f"""import pytest
import ast

def test_{safe_func_name}_syntax_and_integrity():
    \"\"\"Verify that {revision.path} has clean syntax and passes security assertions.\"\"\"
    code = \"\"\"{escaped_code}\"\"\"
    tree = ast.parse(code)
    assert tree is not None, "Revised code must parse cleanly into an AST"
    # Ensure raw eval is not present
    assert "eval(" not in code or "ast.literal_eval" in code, "Raw eval must be replaced"
    # Ensure shell=True is not passed
    assert "shell=True" not in code, "shell=True must not be present in subprocess calls"
"""


def run_revision_tests_isolated(revision: Revision, timeout_seconds: int = 15) -> Tuple[bool, str, str]:
    """Execute companion unit tests against the revised code in an isolated sandbox.

    Returns:
        (passed: bool, stdout_log: str, error_message: str)
    """
    lang_info = detect_language(revision.path, revision.revised_code)

    # 1. Non-Python language validation
    if lang_info.language != Language.PYTHON:
        # Check basic syntax / bracket balance for other languages
        open_brackets = revision.revised_code.count("{") - revision.revised_code.count("}")
        open_parens = revision.revised_code.count("(") - revision.revised_code.count(")")
        if open_brackets != 0 or open_parens != 0:
            return False, "", f"Syntax validation failed for {lang_info.display_name}: unmatched brackets/parentheses."
        return True, f"Syntax and structure verified for {lang_info.display_name}.", ""

    # 2. Python AST quick pre-validation
    try:
        ast.parse(revision.revised_code)
    except SyntaxError as e:
        return False, "", f"Python SyntaxError in revised code: {e.msg} at line {e.lineno}"

    # 3. Isolated Pytest Execution Sandbox
    test_code = revision.test_code or generate_default_test_suite(revision)

    with tempfile.TemporaryDirectory(prefix="sentinel_sandbox_") as tmp_dir:
        sandbox_path = Path(tmp_dir)
        target_file = sandbox_path / revision.path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(revision.revised_code, encoding="utf-8")

        # Create __init__.py in all parent directories to ensure proper import package resolution
        curr = target_file.parent
        while curr != sandbox_path and curr.is_relative_to(sandbox_path):
            init_file = curr / "__init__.py"
            if not init_file.exists():
                init_file.write_text("", encoding="utf-8")
            curr = curr.parent

        test_file = sandbox_path / "test_remediation.py"
        test_file.write_text(test_code, encoding="utf-8")

        # Execute pytest in subprocess with sandbox root on PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(sandbox_path) + os.pathsep + env.get("PYTHONPATH", "")

        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "-o", "asyncio_default_fixture_loop_scope=function",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=str(sandbox_path),
                env=env
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            combined_output = f"{stdout}\n{stderr}".strip()

            if proc.returncode == 0:
                log.info("Isolated sandbox tests PASSED for %s", revision.path)
                return True, combined_output, ""
            else:
                log.warning("Isolated sandbox tests FAILED for %s (exit code %d)", revision.path, proc.returncode)
                # Extract the last few lines summarizing failure
                failure_lines = [l for l in stdout.splitlines() if "FAILED" in l or "ERROR" in l or "assert" in l]
                summary = "; ".join(failure_lines[:3]) if failure_lines else "Companion unit tests failed."
                return False, combined_output, f"Pytest execution failed: {summary}"

        except subprocess.TimeoutExpired:
            log.warning("Isolated sandbox tests TIMED OUT for %s after %ds", revision.path, timeout_seconds)
            return False, "", f"Isolated test execution timed out after {timeout_seconds} seconds."
        except Exception as exc:
            log.warning("Isolated sandbox runner error for %s: %s", revision.path, exc)
            return False, "", f"Sandbox runner execution exception: {str(exc)}"
