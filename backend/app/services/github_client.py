"""Async GitHub REST client for public & private pull-request automation and multi-language review."""
import base64
import logging
import re
from typing import Optional

import httpx

from ..core.config import get_settings


log = logging.getLogger(__name__)


class GitHubError(Exception):
    pass


def parse_repo_and_pr(repo_or_url: str, explicit_pr: Optional[int] = None) -> tuple[str, int]:
    """Parse owner/repo and PR number from either:
    - Full PR URL: https://github.com/owner/repo/pull/42
    - Repo URL + explicit PR: https://github.com/owner/repo, 42
    - SSH format: git@github.com:owner/repo.git, 42
    - Plain format: owner/repo, 42
    """
    raw = repo_or_url.strip()
    pr_num = explicit_pr

    # Match https://github.com/owner/repo/pull/123 (with optional trailing slash or query)
    pr_match = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", raw, re.IGNORECASE)
    if pr_match:
        return pr_match.group(1).rstrip(".git"), int(pr_match.group(2))

    # Match https://github.com/owner/repo
    url_match = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git|/|$)", raw, re.IGNORECASE)
    if url_match:
        repo = url_match.group(1)
        if pr_num is None:
            raise ValueError(f"PR number is required when specifying repository URL '{repo_or_url}'.")
        return repo, int(pr_num)

    # Match git@github.com:owner/repo.git
    ssh_match = re.search(r"github\.com:([^/]+/[^/]+?)(?:\.git|$)", raw, re.IGNORECASE)
    if ssh_match:
        repo = ssh_match.group(1)
        if pr_num is None:
            raise ValueError(f"PR number is required when specifying repository '{repo_or_url}'.")
        return repo, int(pr_num)

    # Match plain owner/repo
    clean = raw.strip("/").rstrip(".git")
    parts = clean.split("/")
    if len(parts) == 2 and parts[0] and parts[1]:
        if pr_num is None:
            raise ValueError(f"PR number is required when specifying repository '{repo_or_url}'.")
        return clean, int(pr_num)

    raise ValueError(
        f"Could not parse a valid GitHub repository or PR URL from '{repo_or_url}'. "
        "Format should be 'owner/repo' or 'https://github.com/owner/repo/pull/<number>'."
    )


class GitHubClient:
    def __init__(self, token: Optional[str] = None) -> None:
        s = get_settings()
        self.token = token or s.github_token
        self.base = s.github_api_url.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CodeSentinel-Audit-Bot",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _require_write_access(self, operation: str) -> None:
        if not self.token:
            raise GitHubError(
                f"A GitHub Personal Access Token (PAT) with repository write permissions is required to {operation}."
            )

    async def _request(self, method: str, path: str, **kw):
        async with httpx.AsyncClient(timeout=60, headers=self.headers) as c:
            r = await c.request(method, f"{self.base}{path}", **kw)

        if r.status_code == 401 or r.status_code == 403:
            msg = r.text[:300]
            if not self.token:
                raise GitHubError(
                    f"GitHub access forbidden ({r.status_code}). A GitHub Personal Access Token (PAT) with 'repo' scope "
                    "is required to access private repositories, perform write operations, or bypass rate limits."
                )
            raise GitHubError(
                f"GitHub access denied ({r.status_code}): {msg}. "
                "Please verify that your Personal Access Token has valid 'repo' and 'pull_requests' scopes."
            )
        if r.status_code == 404:
            raise GitHubError(
                f"GitHub repository or resource not found ({r.status_code}) at {path}. "
                "Ensure the repository exists, is typed correctly, and your token (if private) has access."
            )
        if r.status_code >= 400:
            raise GitHubError(f"GitHub {method} {path} failed: {r.status_code} {r.text[:300]}")
        return r.json() if r.content else {}

    async def get_pull(self, repo: str, number: int) -> dict:
        return await self._request("GET", f"/repos/{repo}/pulls/{number}")

    async def get_repo(self, repo: str) -> dict:
        """Fetch repository metadata and verify access."""
        return await self._request("GET", f"/repos/{repo}")

    async def list_pull_files(self, repo: str, number: int) -> list[dict]:
        files, page = [], 1
        while True:
            batch = await self._request("GET", f"/repos/{repo}/pulls/{number}/files",
                                        params={"per_page": 100, "page": page})
            files += batch
            if len(batch) < 100:
                return files
            page += 1

    async def get_file(self, repo: str, path: str, ref: str) -> tuple[str, str]:
        """Returns (text content, blob sha)."""
        data = await self._request("GET", f"/repos/{repo}/contents/{path}", params={"ref": ref})
        content_bytes = base64.b64decode(data["content"])
        return content_bytes.decode("utf-8", errors="replace"), data["sha"]

    async def create_branch(self, repo: str, name: str, from_sha: str) -> None:
        self._require_write_access("create branches")
        await self._request("POST", f"/repos/{repo}/git/refs",
                            json={"ref": f"refs/heads/{name}", "sha": from_sha})

    async def commit_file(self, repo: str, path: str, content: str, message: str,
                          branch: str, sha: Optional[str] = None) -> None:
        self._require_write_access("commit files")
        payload = {
            "message": message,
            "branch": branch,
            "content": base64.b64encode(content.encode("utf-8")).decode()
        }
        if sha:
            payload["sha"] = sha
        await self._request("PUT", f"/repos/{repo}/contents/{path}", json=payload)

    async def create_pull(self, repo: str, title: str, head: str, base: str, body: str) -> dict:
        self._require_write_access("create pull requests")
        return await self._request("POST", f"/repos/{repo}/pulls",
                                   json={"title": title, "head": head, "base": base, "body": body})

    async def comment(self, repo: str, issue_number: int, body: str) -> dict:
        self._require_write_access("post review comments")
        return await self._request("POST", f"/repos/{repo}/issues/{issue_number}/comments",
                                   json={"body": body})

    async def create_pull_review(self, repo: str, number: int, commit_sha: str, body: str,
                                 comments: Optional[list[dict]] = None, event: str = "COMMENT") -> dict:
        self._require_write_access("create pull request reviews")
        payload = {
            "commit_id": commit_sha,
            "body": body,
            "event": event
        }
        if comments:
            payload["comments"] = comments
        return await self._request("POST", f"/repos/{repo}/pulls/{number}/reviews", json=payload)


def changed_lines_from_patch(patch: Optional[str]) -> Optional[list[int]]:
    """Read the new-file line numbers touched by a unified-diff patch."""
    if not patch:
        return None
    lines, new_no = [], 0
    for row in patch.splitlines():
        if row.startswith("@@"):
            try:
                new_no = int(row.split("+")[1].split(" ")[0].split(",")[0])
            except (IndexError, ValueError):
                return None
            continue
        if row.startswith("+") and not row.startswith("+++"):
            lines.append(new_no)
            new_no += 1
        elif row.startswith("-"):
            continue
        else:
            new_no += 1
    return lines
