"""Test PR autonomous review and auto-revision PR creation."""
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.engine.pipeline import process_pull_request
from backend.app.cli_review_pr import async_main
from backend.app.remediation.fixer import generate_deterministic_revision
from backend.app.core.schemas import Finding, Category, Severity, VerificationStatus


VULNERABLE_PR_CODE = '''def calculate_total(expression):
    # Security defect: unsafe dynamic execution
    result = eval(expression)
    return result
'''


@pytest.mark.asyncio
async def test_process_pull_request_detects_flaws_and_opens_revision_pr(monkeypatch):
    """Verify that when a PR has security vulnerabilities and bugs,

    process_pull_request detects them, creates an ai-review branch,
    commits the remediated code, and opens a new PR targeting the head/base ref.
    """
    mock_gh = AsyncMock()

    # Mock get_pull
    mock_gh.get_pull.return_value = {
        "head": {"ref": "feature/query-runner", "sha": "commit_sha_123"},
        "base": {"ref": "main"}
    }

    # Mock list_pull_files
    mock_gh.list_pull_files.return_value = [
        {
            "filename": "query_runner.py",
            "status": "modified",
            "patch": "@@ -1,4 +1,5 @@\n+def calculate_total(expression):\n+    result = eval(expression)"
        }
    ]

    # Mock get_file
    mock_gh.get_file.return_value = (VULNERABLE_PR_CODE, "blob_sha_456")

    # Mock create_pull
    mock_gh.create_pull.return_value = {
        "html_url": "https://github.com/testorg/testrepo/pull/43",
        "number": 43
    }

    with patch("backend.app.engine.pipeline.GitHubClient", return_value=mock_gh):
        result = await process_pull_request(
            repo="testorg/testrepo",
            pr_number=42,
            token="ghp_test_token_123",
            create_revision_pr=True
        )

    # 1. Verification of review results
    assert result["files"] == 1
    assert result["summary"]["verified"] >= 1
    assert result["revisions_accepted"] >= 1
    assert result["revision_pr"] == "https://github.com/testorg/testrepo/pull/43"

    # 2. Verification of GitHub API interactions
    # Bot commented with the review breakdown
    assert mock_gh.comment.call_count >= 2

    # Bot created a branch starting with ai-review/
    assert mock_gh.create_branch.called
    branch_arg = mock_gh.create_branch.call_args[0][1]
    assert branch_arg.startswith("ai-review/pr-42-")

    # Bot committed corrected file
    assert mock_gh.commit_file.called
    commit_args = mock_gh.commit_file.call_args[0]
    committed_path = commit_args[1]
    committed_code = commit_args[2]

    assert committed_path == "query_runner.py"
    # Unsafe eval and shell=True replaced with safe alternatives
    assert "ast.literal_eval" in committed_code
    assert "shell=True" not in committed_code

    # Bot created the new PR
    assert mock_gh.create_pull.called
    pull_args = mock_gh.create_pull.call_args[0]
    pr_title = pull_args[1]
    pr_branch = pull_args[2]
    assert "Automated Security & Bug Fixes for #42" in pr_title
    assert pr_branch == branch_arg


@pytest.mark.asyncio
async def test_process_pull_request_skips_bot_branch():
    """Bot should not review or loop over its own revision branches."""
    mock_gh = AsyncMock()
    mock_gh.get_pull.return_value = {
        "head": {"ref": "ai-review/pr-42-abc123", "sha": "sha123"},
        "base": {"ref": "main"}
    }
    with patch("backend.app.engine.pipeline.GitHubClient", return_value=mock_gh):
        res = await process_pull_request("testorg/testrepo", 43)
        assert "skipped" in res


@pytest.mark.asyncio
async def test_cli_review_pr_runner(monkeypatch):
    """Test CLI entrypoint runs process_pull_request and returns 0 exit code."""
    fake_result = {
        "files": 1,
        "summary": {"total_findings": 2, "verified": 2},
        "revisions_accepted": 1,
        "revision_pr": "https://github.com/testorg/testrepo/pull/99"
    }
    with patch("backend.app.cli_review_pr.process_pull_request", new=AsyncMock(return_value=fake_result)), \
         patch("sys.argv", ["cli_review_pr", "--repo", "testorg/testrepo", "--pr", "12", "--token", "tok"]):
        exit_code = await async_main()
        assert exit_code == 0


@pytest.mark.asyncio
async def test_process_pull_request_fixes_relative_import_bug():
    """Verify that relative-beyond-top-level import bugs are detected,
    remediated, and trigger a revision PR even with LLM offline.
    """
    mock_gh = AsyncMock()
    mock_gh.get_pull.return_value = {
        "head": {"ref": "feature/main-fix", "sha": "sha_main_123"},
        "base": {"ref": "main"}
    }
    mock_gh.list_pull_files.return_value = [
        {
            "filename": "backend/main.py",
            "status": "modified",
            "patch": "@@ -1,3 +1,3 @@\n+from .app.main import app"
        }
    ]
    mock_gh.get_file.return_value = (
        '"""Backend root entrypoint proxying to backend.app.main."""\nfrom .app.main import app\n\n__all__ = ["app"]\n',
        "blob_sha_main"
    )
    mock_gh.create_pull.return_value = {
        "html_url": "https://github.com/testorg/testrepo/pull/44",
        "number": 44
    }

    with patch("backend.app.engine.pipeline.GitHubClient", return_value=mock_gh):
        result = await process_pull_request("testorg/testrepo", 10, create_revision_pr=True)

    assert result["summary"]["verified"] >= 1
    assert result["revisions_accepted"] == 1
    assert result["revision_pr"] == "https://github.com/testorg/testrepo/pull/44"
    assert mock_gh.create_pull.called
    assert mock_gh.commit_file.called
    committed_code = mock_gh.commit_file.call_args[0][2]
    assert "from .app.main" not in committed_code


@pytest.mark.asyncio
async def test_process_pull_request_compulsorily_raises_pr_even_on_clean_code():
    """Verify that even when a PR has 0 verified defects (clean code),
    process_pull_request compulsorily creates an isolated branch,
    commits automated companion regression tests, and opens a revision PR.
    """
    mock_gh = AsyncMock()
    mock_gh.get_pull.return_value = {
        "head": {"ref": "feature/clean-code", "sha": "clean_sha_789"},
        "base": {"ref": "main"}
    }
    clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    mock_gh.list_pull_files.return_value = [
        {
            "filename": "math_utils.py",
            "status": "modified",
            "patch": "@@ -1,2 +1,2 @@\n+def add(a: int, b: int) -> int:\n+    return a + b"
        }
    ]
    mock_gh.get_file.return_value = (clean_code, "blob_sha_math")
    mock_gh.create_pull.return_value = {
        "html_url": "https://github.com/testorg/testrepo/pull/55",
        "number": 55
    }

    with patch("backend.app.engine.pipeline.GitHubClient", return_value=mock_gh):
        result = await process_pull_request("testorg/testrepo", 15, create_revision_pr=True)

    # Must compulsorily open a revision PR with companion tests
    assert result["summary"]["verified"] == 0
    assert result["revisions_accepted"] == 1
    assert result["revision_pr"] == "https://github.com/testorg/testrepo/pull/55"
    assert mock_gh.create_branch.called
    assert mock_gh.commit_file.called
    assert mock_gh.create_pull.called
    pull_args = mock_gh.create_pull.call_args[0]
    assert "Verification & Quality Hardening for #15" in pull_args[1]

