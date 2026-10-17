"""Small async client for any OpenAI-compatible chat API (default: NVIDIA NIM)."""
import asyncio
import json
import logging
import re
from typing import Any, Optional

import httpx

from ..core.config import get_settings


log = logging.getLogger(__name__)


def extract_json(text: str) -> Optional[Any]:
    """Pull the first JSON object or array out of a model reply."""
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    return None


class LLMClient:
    def __init__(self) -> None:
        self._sem: Optional[asyncio.Semaphore] = None
        self._circuit_broken_until: float = 0.0

    @property
    def enabled(self) -> bool:
        import time
        if time.time() < self._circuit_broken_until:
            return False
        return get_settings().llm_ready

    def _semaphore(self) -> asyncio.Semaphore:
        if self._sem is None:
            self._sem = asyncio.Semaphore(max(1, get_settings().llm_concurrency))
        return self._sem

    async def chat_json(self, system: str, user: str, *, task: str = "", max_tokens: int = 4096) -> Optional[Any]:
        """Ask the model for JSON. Returns None when the LLM is off or fails."""
        import time
        s = get_settings()
        if not self.enabled:
            return None
        payload = {
            "model": s.llm_model,
            "temperature": s.llm_temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        headers = {"Authorization": f"Bearer {s.llm_api_key}", "Content-Type": "application/json"}
        url = s.llm_base_url.rstrip("/") + "/chat/completions"
        timeout = min(s.llm_timeout, 8.0)
        async with self._semaphore():
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    r = await client.post(url, headers=headers, json=payload)
                    r.raise_for_status()
                parsed = extract_json(r.json()["choices"][0]["message"]["content"])
                if parsed is not None:
                    return parsed
                log.warning("LLM task %s returned non-JSON", task)
            except Exception as exc:
                log.warning("LLM task %s failed (%s). Tripping circuit breaker for 60s to prevent hang.", task, exc)
                self._circuit_broken_until = time.time() + 60.0
        return None


llm_client = LLMClient()
