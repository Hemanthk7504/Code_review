"""Minimal async GitHub REST client for pull-request automation."""
import base64
from typing import Optional

import httpx

from ..core.config import get_settings



class GitHubError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: Optional[str] = None) -> None:
        s = get_settings()
        self.token = token or s.github_token
        if not self.token:
            raise GitHubError("No GitHub token. Set GITHUB_TOKEN or pass github_token.")
        self.base = s.github_api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(self, method: str, path: str, **kw):
        async with httpx.AsyncClient(timeout=60, headers=self.headers) as c:
            r = await c.request(method, f"{self.base}{path}", **kw)
        if r.status_code >= 400:
            raise GitHubError(f"GitHub {method} {path} failed: {r.status_code} {r.text[:300]}")
        return r.json() if r.content else {}

    async def get_pull(self, repo: str, number: int) -> dict:
        return await self._request("GET", f"/repos/{repo}/pulls/{number}")

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
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace"), data["sha"]

    async def create_branch(self, repo: str, name: str, from_sha: str) -> None:
        await self._request("POST", f"/repos/{repo}/git/refs",
                            json={"ref": f"refs/heads/{name}", "sha": from_sha})

    async def commit_file(self, repo: str, path: str, content: str, message: str,
                          branch: str, sha: str) -> None:
        await self._request("PUT", f"/repos/{repo}/contents/{path}", json={
            "message": message, "branch": branch, "sha": sha,
            "content": base64.b64encode(content.encode("utf-8")).decode()})

    async def create_pull(self, repo: str, title: str, head: str, base: str, body: str) -> dict:
        return await self._request("POST", f"/repos/{repo}/pulls",
                                   json={"title": title, "head": head, "base": base, "body": body})

    async def comment(self, repo: str, issue_number: int, body: str) -> dict:
        return await self._request("POST", f"/repos/{repo}/issues/{issue_number}/comments",
                                   json={"body": body})


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
