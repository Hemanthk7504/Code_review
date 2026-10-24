"""Small async client for any OpenAI-compatible chat API (default: NVIDIA NIM) with retries, JSON auto-repair, and diagnostics."""
import asyncio
import json
import logging
import re
import time
from typing import Any, Optional

import httpx

from ..core.config import get_settings


log = logging.getLogger(__name__)


def repair_json_string(text: str) -> Optional[Any]:
    """Attempt basic repairs on malformed JSON strings."""
    clean = text.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)
    clean = clean.strip()

    # 1. Standard parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # 2. Remove trailing commas before closing braces/brackets
    clean_no_trailing = re.sub(r",\s*([}\]])", r"\1", clean)
    try:
        return json.loads(clean_no_trailing)
    except json.JSONDecodeError:
        pass

    # 3. Handle unclosed brackets / braces
    stack = []
    in_string = False
    escape = False
    for ch in clean_no_trailing:
        if ch == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]":
                if stack and stack[-1] == ch:
                    stack.pop()
        escape = (ch == "\\" and not escape)

    repaired = clean_no_trailing
    if in_string:
        repaired += '"'
    while stack:
        repaired += stack.pop()

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    return None


def extract_json(text: str) -> Optional[Any]:
    """Extract and parse the first valid JSON object or array out of a model response."""
    if not text:
        return None

    # First attempt direct parse / repair
    direct = repair_json_string(text)
    if direct is not None:
        return direct

    # Scan for first opening brace or bracket
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                sub = repair_json_string(text[i:])
                if sub is not None:
                    return sub
                continue
    return None


class LLMClient:
    def __init__(self) -> None:
        self._sem: Optional[asyncio.Semaphore] = None
        self._circuit_broken_until: float = 0.0
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.retried_requests: int = 0
        self.consecutive_failures: int = 0
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[float] = None

    @property
    def enabled(self) -> bool:
        if time.time() < self._circuit_broken_until:
            return False
        return get_settings().llm_ready

    def _semaphore(self) -> asyncio.Semaphore:
        if self._sem is None:
            self._sem = asyncio.Semaphore(max(1, get_settings().llm_concurrency))
        return self._sem

    def get_diagnostics(self) -> dict:
        """Structured diagnostic report for LLM availability and health."""
        s = get_settings()
        now = time.time()
        is_circuit_broken = now < self._circuit_broken_until
        return {
            "configured": s.llm_ready,
            "enabled": self.enabled,
            "circuit_broken": is_circuit_broken,
            "circuit_breaker_remaining_seconds": max(0, int(self._circuit_broken_until - now)),
            "model": s.llm_model,
            "endpoint": s.llm_base_url,
            "timeout_seconds": s.llm_timeout,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retried_requests": self.retried_requests,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
        }

    async def chat_json(self, system: str, user: str, *, task: str = "", max_tokens: int = 4096) -> Optional[Any]:
        """Ask the model for JSON with retries, timeout handling, and diagnostic tracking."""
        s = get_settings()
        if not self.enabled:
            return None

        self.total_requests += 1
        payload = {
            "model": s.llm_model,
            "temperature": s.llm_temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        headers = {"Authorization": f"Bearer {s.effective_llm_api_key}", "Content-Type": "application/json"}
        url = s.llm_base_url.rstrip("/") + "/chat/completions"
        timeout = s.llm_timeout

        max_attempts = 3
        async with self._semaphore():
            for attempt in range(1, max_attempts + 1):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        r = await client.post(url, headers=headers, json=payload)
                        if r.status_code == 429 or r.status_code >= 500:
                            if attempt < max_attempts:
                                self.retried_requests += 1
                                backoff = min(2 ** attempt, 8)
                                log.warning("LLM task '%s' received status %d. Retrying in %ds (attempt %d/%d)...",
                                            task, r.status_code, backoff, attempt, max_attempts)
                                await asyncio.sleep(backoff)
                                continue
                        r.raise_for_status()

                    resp_data = r.json()
                    choices = resp_data.get("choices", [])
                    if not choices:
                        raise ValueError("No choices returned from LLM completion.")
                    raw_content = choices[0].get("message", {}).get("content", "")
                    parsed = extract_json(raw_content)
                    if parsed is not None:
                        self.successful_requests += 1
                        self.consecutive_failures = 0
                        return parsed

                    log.warning("LLM task '%s' returned non-JSON content: %s", task, raw_content[:200])
                    # If parsing failed, retry if attempts remain
                    if attempt < max_attempts:
                        self.retried_requests += 1
                        await asyncio.sleep(1)
                        continue

                except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                    if attempt < max_attempts:
                        self.retried_requests += 1
                        backoff = min(2 ** attempt, 8)
                        log.warning("LLM network/timeout on task '%s' (%s). Retrying in %ds (attempt %d/%d)...",
                                    task, net_err, backoff, attempt, max_attempts)
                        await asyncio.sleep(backoff)
                        continue
                    self._record_failure(f"Network/timeout error: {net_err}", task)
                    return None
                except Exception as exc:
                    self._record_failure(str(exc), task)
                    return None

        self._record_failure(f"Failed after {max_attempts} attempts", task)
        return None

    def _record_failure(self, err_msg: str, task: str) -> None:
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_error = f"Task '{task}': {err_msg}"
        self.last_error_time = time.time()
        log.warning("LLM call failed for task '%s': %s (consecutive failures: %d)",
                    task, err_msg, self.consecutive_failures)
        # Only trip circuit breaker after 3 consecutive failure cascades
        if self.consecutive_failures >= 3:
            self._circuit_broken_until = time.time() + 30.0
            log.error("Tripping LLM circuit breaker for 30s after %d consecutive failures.", self.consecutive_failures)


llm_client = LLMClient()
