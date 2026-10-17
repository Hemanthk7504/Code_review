"""Quality Gates and Automated Governance Policy Engine."""
import logging
from typing import Any, Optional

from ..core.schemas import (Finding, PolicyEvaluationResult, PolicyRuleEvaluation,
                      QualityGatePolicy, ReviewResult, Severity, VerificationStatus)


logger = logging.getLogger(__name__)

# Active quality gate policy
_ACTIVE_POLICY = QualityGatePolicy(
    name="Enterprise Strict Gate (Production)",
    max_risk_score=35.0,
    block_on_critical=True,
    block_on_high=True,
    block_on_secrets=True,
    max_unresolved_findings=4,
    require_syntax_check=True,
    min_verification_confidence=0.6,
)


def get_active_policy() -> QualityGatePolicy:
    """Return currently active Quality Gate policy."""
    return _ACTIVE_POLICY


def set_active_policy(policy: QualityGatePolicy) -> QualityGatePolicy:
    """Update active Quality Gate policy."""
    global _ACTIVE_POLICY
    _ACTIVE_POLICY = policy
    return _ACTIVE_POLICY


def evaluate_quality_gate(
    review_result: Any,
    policy: Optional[QualityGatePolicy] = None
) -> PolicyEvaluationResult:
    """Evaluate a code review result against enterprise security & quality policies."""
    p = policy or _ACTIVE_POLICY
    evaluations: list[PolicyRuleEvaluation] = []
    violations: list[str] = []

    findings = getattr(review_result, "findings", []) or []
    verified_findings = [
        f for f in findings
        if f.verification in (VerificationStatus.verified, VerificationStatus.uncertain)
    ]
    critical_findings = [f for f in verified_findings if f.severity == Severity.critical]
    high_findings = [f for f in verified_findings if f.severity == Severity.high]
    secret_findings = [
        f for f in verified_findings
        if "secret" in f.rule_id.lower() or f.cwe_id == "CWE-798" or "secret_scanner" in f.sources
    ]

    # 1. Check Max Risk Score
    overall_risk = 0.0
    if hasattr(review_result, "summary") and review_result.summary:
        if isinstance(review_result.summary, dict):
            overall_risk = float(review_result.summary.get("overall_risk", 0.0))
        elif hasattr(review_result.summary, "overall_risk"):
            overall_risk = float(review_result.summary.overall_risk)
    elif hasattr(review_result, "overall_risk") and review_result.overall_risk is not None:
        overall_risk = float(review_result.overall_risk)
    else:
        from .risk import overall_risk as calc_overall_risk
        overall_risk = calc_overall_risk(findings)

    risk_passed = overall_risk <= p.max_risk_score
    if not risk_passed:
        violations.append(
            f"Overall risk score {overall_risk:.1f} exceeds quality gate limit of {p.max_risk_score:.1f}"
        )
    evaluations.append(PolicyRuleEvaluation(
        rule="Maximum Allowed Risk Score",
        passed=risk_passed,
        message=f"Current risk: {overall_risk:.1f} / Limit: {p.max_risk_score:.1f}",
        details={"risk": overall_risk, "threshold": p.max_risk_score}
    ))

    # 2. Block on Critical Severity
    if p.block_on_critical:
        crit_passed = len(critical_findings) == 0
        if not crit_passed:
            violations.append(
                f"Blocked by {len(critical_findings)} unmitigated critical vulnerability(ies)."
            )
        evaluations.append(PolicyRuleEvaluation(
            rule="Zero Critical Vulnerabilities",
            passed=crit_passed,
            message=f"{len(critical_findings)} critical findings detected",
            details={"count": len(critical_findings)}
        ))

    # 3. Block on High Severity
    if p.block_on_high:
        high_passed = len(high_findings) == 0
        if not high_passed:
            violations.append(
                f"Blocked by {len(high_findings)} high severity finding(s)."
            )
        evaluations.append(PolicyRuleEvaluation(
            rule="Zero High Severity Vulnerabilities",
            passed=high_passed,
            message=f"{len(high_findings)} high findings detected",
            details={"count": len(high_findings)}
        ))

    # 4. Block on Secrets / Credentials
    if p.block_on_secrets:
        secrets_passed = len(secret_findings) == 0
        if not secrets_passed:
            violations.append(
                f"Critical security violation: {len(secret_findings)} hardcoded secret(s) or API credential(s) detected."
            )
        evaluations.append(PolicyRuleEvaluation(
            rule="No Hardcoded Secrets / Tokens",
            passed=secrets_passed,
            message=f"{len(secret_findings)} exposed secrets detected",
            details={"count": len(secret_findings)}
        ))

    # 5. Max Unresolved Findings Count
    findings_passed = len(verified_findings) <= p.max_unresolved_findings
    if not findings_passed:
        violations.append(
            f"Verified findings count ({len(verified_findings)}) exceeds limit of {p.max_unresolved_findings}."
        )
    evaluations.append(PolicyRuleEvaluation(
        rule="Maximum Unresolved Findings",
        passed=findings_passed,
        message=f"{len(verified_findings)} verified findings (max allowed: {p.max_unresolved_findings})",
        details={"count": len(verified_findings), "max": p.max_unresolved_findings}
    ))

    # Determine Gate Outcome
    all_passed = len(violations) == 0
    if all_passed:
        status = "PASSED"
    elif any(rule.rule in ("Zero Critical Vulnerabilities", "No Hardcoded Secrets / Tokens") for rule in evaluations if not rule.passed):
        status = "BLOCKED"
    elif overall_risk > p.max_risk_score:
        status = "BLOCKED"
    else:
        status = "WARNING"

    # Compute a 0-100 Gate Score
    passed_rules_count = sum(1 for e in evaluations if e.passed)
    score = (passed_rules_count / len(evaluations) * 100.0) if evaluations else 100.0

    return PolicyEvaluationResult(
        gate_name=p.name,
        status=status,
        passed=all_passed,
        score=round(score, 1),
        violations=violations,
        evaluations=evaluations,
    )
