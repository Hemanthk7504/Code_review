"""Risk-adaptive engine: scores each finding and the overall risk of a set of findings.

finding score (0-100) = 100 * (0.35*severity + 0.20*confidence + 0.20*security impact
                               + 0.15*code impact + 0.10*evidence strength)
"""
from typing import Optional

from ..core.schemas import SEVERITY_WEIGHT, Category, Finding, FileInput, VerificationStatus


W_SEVERITY, W_CONFIDENCE, W_SECURITY, W_IMPACT, W_EVIDENCE = 0.35, 0.20, 0.20, 0.15, 0.10

_SECURITY_IMPACT = {
    Category.security: 1.0, Category.bug: 0.5, Category.performance: 0.3,
    Category.complexity: 0.2, Category.quality: 0.15, Category.refactor: 0.1, Category.style: 0.05,
}


def priority_label(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _code_impact(f: Finding, changed: Optional[set[int]]) -> float:
    if changed is None:
        return 0.8
    span = range(f.line, (f.end_line or f.line) + 1)
    return 1.0 if any(n in changed for n in span) else 0.5


def _evidence_strength(f: Finding) -> float:
    strength = 0.5 * len(f.static_sources) + (0.3 if f.ai_sources else 0.0)
    if len(f.ai_sources) > 1:
        strength += 0.2
    return min(1.0, strength)


def score_finding(f: Finding, changed: Optional[set[int]] = None) -> float:
    score = (W_SEVERITY * SEVERITY_WEIGHT[f.severity] + W_CONFIDENCE * f.confidence
             + W_SECURITY * _SECURITY_IMPACT.get(f.category, 0.1)
             + W_IMPACT * _code_impact(f, changed) + W_EVIDENCE * _evidence_strength(f))
    return round(100 * score, 2)


def apply_risk(findings: list[Finding], files: list[FileInput]) -> list[Finding]:
    changed = {f.path: (set(f.changed_lines) if f.changed_lines is not None else None) for f in files}
    for f in findings:
        f.risk_score = score_finding(f, changed.get(f.file))
        f.priority = priority_label(f.risk_score)
    findings.sort(key=lambda f: f.risk_score, reverse=True)
    return findings


def overall_risk(findings: list[Finding]) -> float:
    """Combine finding scores into one 0-100 number. Rejected findings do not count."""
    remaining = 1.0
    for f in findings:
        if f.verification == VerificationStatus.rejected:
            continue
        remaining *= 1 - 0.6 * (f.risk_score / 100)
    return round(100 * (1 - remaining), 2)


def calculate_posture_grade(score: float) -> str:
    """Map overall risk score (0-100) to an industry security posture grade."""
    if score <= 15:
        return "A+"
    if score <= 30:
        return "A"
    if score <= 50:
        return "B"
    if score <= 70:
        return "C"
    if score <= 85:
        return "D"
    return "F"


def extract_top_risks(findings: list[Finding], limit: int = 3) -> list[str]:
    """Extract human-readable highlights of the top risk items."""
    live = [f for f in findings if f.verification != VerificationStatus.rejected]
    live.sort(key=lambda f: f.risk_score, reverse=True)
    out = []
    for f in live[:limit]:
        cwe_str = f" [{f.cwe_id}]" if f.cwe_id else ""
        out.append(f"{f.priority.upper()}: {f.title}{cwe_str} at {f.file}:{f.line} (risk {f.risk_score})")
    return out


def summarize_cwe_counts(findings: list[Finding]) -> dict[str, int]:
    """Aggregate finding counts by CWE identifier."""
    counts: dict[str, int] = {}
    for f in findings:
        if f.verification != VerificationStatus.rejected and f.cwe_id:
            counts[f.cwe_id] = counts.get(f.cwe_id, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
