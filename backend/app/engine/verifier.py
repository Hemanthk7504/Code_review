"""Self-verification: cross-check findings against the source code and static-analysis evidence.

Each finding ends as verified, rejected or uncertain. The confidence needed to verify an
AI-only finding rises with its risk score (risk-adaptive threshold).
"""
import asyncio
import re

from .agents import numbered
from ..core.config import get_settings
from .llm import llm_client
from ..core.schemas import Finding, VerificationStatus


VERIFIER_SYSTEM = (
    "You are an independent verifier in a code review system. You are given source code and one "
    "claimed issue. Decide from the code alone whether the issue is real. Be skeptical: refute claims "
    "that the code does not support. Reply with JSON only: "
    '{"verdict": "confirmed|refuted|unsure", "confidence": <0.0-1.0>, "reason": "<one sentence>"}'
)


def adaptive_threshold(risk_score: float) -> float:
    s = get_settings()
    return min(0.95, s.verify_base_threshold + s.verify_risk_weight * (risk_score / 100))


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _window(lines: list[str], line: int, radius: int) -> str:
    lo, hi = max(1, line - radius), min(len(lines), line + radius)
    return "\n".join(f"{i:>4}: {lines[i - 1]}" for i in range(lo, hi + 1))


def _snippet_matches(f: Finding, lines: list[str]) -> bool:
    if not f.code_snippet:
        return False
    lo, hi = max(0, f.line - 4), min(len(lines), (f.end_line or f.line) + 3)
    region = _norm("".join(lines[lo:hi]))
    return _norm(f.code_snippet) in region


def _set(f: Finding, status: VerificationStatus, reason: str, conf: float | None = None) -> None:
    f.verification, f.verification_reason, f.verification_confidence = status, reason, conf


async def _verify_one(f: Finding, content: str) -> None:
    lines = content.splitlines()
    if f.line < 1 or f.line > max(1, len(lines)):
        return _set(f, VerificationStatus.rejected, "Reported line does not exist in the file.", 1.0)

    if f.static_sources:
        return _set(f, VerificationStatus.verified,
                    f"Confirmed by static analysis ({', '.join(f.static_sources)}).", f.confidence)

    snippet_ok = _snippet_matches(f, lines)
    if not llm_client.enabled:
        if snippet_ok:
            return _set(f, VerificationStatus.uncertain,
                        "Code matches the AI claim, but no independent verifier is available.", f.confidence)
        return _set(f, VerificationStatus.rejected,
                    "AI finding has no static evidence and its code snippet does not match the file.", 0.8)

    user = (f"Claimed issue ({f.category.value}, {f.severity.value}): {f.title}\n"
            f"Details: {f.description}\nReported near line {f.line}.\n\n"
            f"Code around the reported line:\n{_window(lines, f.line, 15)}\n\n"
            f"If you need more context, this is the whole file:\n{numbered(content)}")
    data = await llm_client.chat_json(VERIFIER_SYSTEM, user, task="verify", max_tokens=400)
    if not isinstance(data, dict):
        return _set(f, VerificationStatus.uncertain, "Verifier did not return a usable answer.", None)

    verdict = str(data.get("verdict", "unsure")).lower()
    reason = str(data.get("reason", ""))[:300]
    try:
        conf = min(1.0, max(0.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    threshold = adaptive_threshold(f.risk_score)

    if verdict == "refuted" and conf >= 0.5:
        return _set(f, VerificationStatus.rejected, f"Verifier refuted the finding: {reason}", conf)
    if verdict == "confirmed" and conf >= threshold and snippet_ok:
        return _set(f, VerificationStatus.verified, f"Verifier confirmed (needed {threshold:.2f}): {reason}", conf)
    if verdict == "confirmed" and conf >= threshold:
        return _set(f, VerificationStatus.uncertain,
                    f"Verifier confirmed but the quoted code does not match the file: {reason}", conf)
    return _set(f, VerificationStatus.uncertain,
                f"Not enough confidence (verdict={verdict}, {conf:.2f} < {threshold:.2f}): {reason}", conf)


async def verify_findings(findings: list[Finding], contents: dict[str, str]) -> list[Finding]:
    await asyncio.gather(*(_verify_one(f, contents.get(f.file, "")) for f in findings))
    return findings
