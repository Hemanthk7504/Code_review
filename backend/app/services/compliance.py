"""Compliance & Regulatory Security Framework Mapping (OWASP Top 10, SOC 2, PCI-DSS)."""
from typing import Any

from ..core.schemas import ComplianceItem, ComplianceScorecardResult, Finding, VerificationStatus


OWASP_CONTROLS = [
    {
        "id": "A01:2021",
        "name": "Broken Access Control",
        "description": "Restrictions on what authenticated users are allowed to do are not properly enforced.",
        "cwes": ["CWE-22", "CWE-284", "CWE-862", "CWE-863"],
    },
    {
        "id": "A02:2021",
        "name": "Cryptographic Failures",
        "description": "Sensitive data exposure and use of weak or broken cryptographic algorithms / hardcoded keys.",
        "cwes": ["CWE-259", "CWE-327", "CWE-328", "CWE-330", "CWE-798"],
    },
    {
        "id": "A03:2021",
        "name": "Injection",
        "description": "Hostile data sent to an interpreter as part of a command or query (SQL, OS command, Eval).",
        "cwes": ["CWE-78", "CWE-79", "CWE-89", "CWE-94", "CWE-116"],
    },
    {
        "id": "A04:2021",
        "name": "Insecure Design",
        "description": "Risks related to design flaws and missing threat modeling or architectural controls.",
        "cwes": ["CWE-209", "CWE-400"],
    },
    {
        "id": "A05:2021",
        "name": "Security Misconfiguration",
        "description": "Insecure default configurations, open cloud storage, verbose error messages.",
        "cwes": ["CWE-16", "CWE-200", "CWE-215", "CWE-1004"],
    },
    {
        "id": "A06:2021",
        "name": "Vulnerable and Outdated Components",
        "description": "Using client or server components with known vulnerabilities without active patching.",
        "cwes": ["CWE-1104"],
    },
    {
        "id": "A07:2021",
        "name": "Identification & Authentication Failures",
        "description": "Weak session management, credential stuffing vulnerability, or missing auth checks.",
        "cwes": ["CWE-287", "CWE-384", "CWE-798"],
    },
    {
        "id": "A08:2021",
        "name": "Software and Data Integrity Failures",
        "description": "Unsafe code deserialization (pickle), unverified firmware/plugins, CI/CD pipeline tampering.",
        "cwes": ["CWE-502", "CWE-829"],
    },
    {
        "id": "A09:2021",
        "name": "Security Logging and Monitoring Failures",
        "description": "Lack of auditing, insufficient log context, undetected breach attempts.",
        "cwes": ["CWE-778", "CWE-117"],
    },
    {
        "id": "A10:2021",
        "name": "Server-Side Request Forgery (SSRF)",
        "description": "Web applications fetching a remote resource without validating the user-supplied URL.",
        "cwes": ["CWE-918"],
    },
]

SOC2_CONTROLS = [
    {
        "id": "CC6.1",
        "name": "Logical Access Security",
        "description": "Controls to prevent unauthorized access to codebase and confidential application data.",
        "cwes": ["CWE-284", "CWE-287", "CWE-798"],
    },
    {
        "id": "CC6.6",
        "name": "Boundary & Threat Protection",
        "description": "Mechanisms guarding against external malicious traffic and unauthorized commands.",
        "cwes": ["CWE-78", "CWE-89", "CWE-94"],
    },
    {
        "id": "CC6.8",
        "name": "Unauthorized Code Prevention",
        "description": "Prevention of malicious code injection and arbitrary execution within execution environments.",
        "cwes": ["CWE-94", "CWE-502"],
    },
    {
        "id": "CC7.1",
        "name": "Vulnerability Detection & Management",
        "description": "Automated detection of security defects prior to release into production environments.",
        "cwes": ["CWE-20", "CWE-200"],
    },
]

PCI_DSS_CONTROLS = [
    {
        "id": "Req 6.2.4",
        "name": "Injection Flaw Prevention",
        "description": "Mitigating SQL injection, OS command injection, and dynamic code evaluation.",
        "cwes": ["CWE-78", "CWE-89", "CWE-94"],
    },
    {
        "id": "Req 6.3.2",
        "name": "Pre-Release Security Code Review",
        "description": "Verifying that custom application code is systematically reviewed for vulnerabilities.",
        "cwes": ["CWE-798", "CWE-22", "CWE-327"],
    },
    {
        "id": "Req 6.4.1",
        "name": "Rapid Vulnerability Remediation",
        "description": "Ensuring critical vulnerabilities are prioritized and resolved with verified fixes.",
        "cwes": ["CWE-502", "CWE-798"],
    },
]


def generate_compliance_scorecard(findings: list[Finding], framework: str = "OWASP_TOP_10") -> ComplianceScorecardResult:
    """Evaluate review findings against standard compliance frameworks."""
    framework = framework.upper()
    if framework == "SOC_2":
        controls_def = SOC2_CONTROLS
        framework_title = "SOC 2 Type II Security Controls"
    elif framework == "PCI_DSS":
        controls_def = PCI_DSS_CONTROLS
        framework_title = "PCI-DSS v4.0 Requirement 6"
    else:
        controls_def = OWASP_CONTROLS
        framework_title = "OWASP Top 10 (2021)"

    verified_findings = [
        f for f in findings
        if f.verification in (VerificationStatus.verified, VerificationStatus.uncertain)
    ]

    items: list[ComplianceItem] = []
    compliant_controls = 0

    for c in controls_def:
        matched_findings = [
            f for f in verified_findings
            if (f.cwe_id and f.cwe_id in c["cwes"]) or any(cw.lower() in f.rule_id.lower() for cw in c["cwes"])
        ]
        count = len(matched_findings)
        if count == 0:
            status = "COMPLIANT"
            compliant_controls += 1
        elif count <= 2 and all(f.severity.value in ("low", "info") for f in matched_findings):
            status = "PARTIALLY_COMPLIANT"
        else:
            status = "NON_COMPLIANT"

        items.append(ComplianceItem(
            id=c["id"],
            name=c["name"],
            description=c["description"],
            status=status,
            finding_count=count,
            associated_cwes=c["cwes"],
        ))

    score = (compliant_controls / len(controls_def) * 100.0) if controls_def else 100.0

    return ComplianceScorecardResult(
        framework=framework_title,
        compliance_score=round(score, 1),
        compliant_controls=compliant_controls,
        total_controls=len(controls_def),
        items=items,
    )
