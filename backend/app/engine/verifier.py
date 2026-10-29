"""Self-verification: cross-check findings against the source code and static-analysis evidence.

Each finding ends as verified, rejected or uncertain. Implements evidence-based verification
to eliminate false positives (e.g. parameterized SQL queries, safe literal_eval, test mocks,
shell=False lists) even if static analysis or AI initially raised an alert.
"""
import asyncio
import re

from .agents import numbered
from ..core.config import get_settings
from .evidence_checker import verify_evidence
from .llm import llm_client
from ..core.schemas import Finding, VerificationStatus


VERIFIER_SYSTEM = (
    "You are an independent skeptical verifier in an advanced code review system. You are given source code "
    "and one claimed issue. Decide from the code context alone whether the issue is genuine or a FALSE POSITIVE. "
    "Be highly skeptical: static analysis tools often misidentify safe patterns (such as parameterized queries, "
    "safe literal_eval, shell=False argument lists, dummy test fixtures/placeholders, or sanitized inputs). "
    "If the code is safe, sanitized, or not vulnerable as claimed, you MUST reply with 'refuted'. "
    "Reply with JSON only: "
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

    # 1. Deep Syntactic & AST Evidence Check (Deterministic False-Positive Defense)
    ev_verdict, ev_reason, ev_conf = verify_evidence(f, content)
    if ev_verdict == "refuted":
        return _set(f, VerificationStatus.rejected, f"Evidence-based check refuted finding: {ev_reason}", ev_conf)

    snippet_ok = _snippet_matches(f, lines)

    # 2. If LLM is not enabled, use evidence check + static corroboration
    if not llm_client.enabled:
        if ev_verdict == "confirmed":
            return _set(f, VerificationStatus.verified, f"Evidence-based check confirmed vulnerability: {ev_reason}", ev_conf)
        if f.static_sources and snippet_ok:
            return _set(f, VerificationStatus.verified,
                        f"Corroborated by static analysis ({', '.join(f.static_sources)}) with confirmed code context.",
                        f.confidence or 0.88)
        if snippet_ok:
            return _set(f, VerificationStatus.uncertain,
                        "Code snippet exists, but independent verifier is unavailable to confirm.", f.confidence)
        return _set(f, VerificationStatus.rejected,
                    "Finding has no corroborating static evidence and its code snippet does not match the file.", 0.85)

    # 3. LLM-Based Skeptical Cross-Verification (Evaluates code context with skeptical prompt)
    user = (f"Claimed issue ({f.category.value}, {f.severity.value}): {f.title}\n"
            f"Details: {f.description}\nReported near line {f.line}.\n"
            f"Static sources claiming this: {', '.join(f.static_sources) if f.static_sources else 'None'}\n\n"
            f"Code around the reported line:\n{_window(lines, f.line, 15)}\n\n"
            f"If you need more context, this is the whole file:\n{numbered(content)}")
    data = await llm_client.chat_json(VERIFIER_SYSTEM, user, task="verify", max_tokens=2048)
    if not isinstance(data, dict):
        # Fallback to evidence check if LLM response unavailable
        if ev_verdict == "confirmed" or (f.static_sources and snippet_ok):
            return _set(f, VerificationStatus.verified,
                        f"Confirmed by static/AST evidence ({', '.join(f.static_sources or ['AST Checker'])}).", 0.85)
        return _set(f, VerificationStatus.uncertain, "Verifier did not return a usable answer.", None)

    verdict = str(data.get("verdict", "unsure")).lower()
    reason = str(data.get("reason", ""))[:300]
    try:
        conf = min(1.0, max(0.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    threshold = adaptive_threshold(f.risk_score)

    if verdict == "refuted" and conf >= 0.5:
        return _set(f, VerificationStatus.rejected, f"Skeptical verifier refuted the finding: {reason}", conf)
    if verdict == "confirmed" and conf >= threshold and snippet_ok:
        return _set(f, VerificationStatus.verified, f"Verifier confirmed (needed {threshold:.2f}): {reason}", conf)
    if verdict == "confirmed" and conf >= threshold:
        return _set(f, VerificationStatus.uncertain,
                    f"Verifier confirmed but the quoted code does not match the file: {reason}", conf)
    if ev_verdict == "confirmed" and f.static_sources and snippet_ok:
        return _set(f, VerificationStatus.verified,
                    f"Confirmed by AST code evidence ({ev_reason}) and {', '.join(f.static_sources)}.", ev_conf)
    return _set(f, VerificationStatus.uncertain,
                f"Not enough confidence (verdict={verdict}, {conf:.2f} < {threshold:.2f}): {reason}", conf)


async def verify_findings(findings: list[Finding], contents: dict[str, str]) -> list[Finding]:
    await asyncio.gather(*(_verify_one(f, contents.get(f.file, "")) for f in findings))
    return findings
