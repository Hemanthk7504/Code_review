"""Taxonomy mapping: Maps static analysis rules and finding categories to CWE and OWASP standards.

Provides industry-standard vulnerability classifications and effort estimation.
"""
from typing import Dict, Tuple

from ..core.schemas import Category, Finding, Severity



# Direct rule mappings: rule_id -> (CWE ID, OWASP category, remediation_effort)
RULE_MAPPINGS: Dict[str, Tuple[str, str, str]] = {
    # AST Rules
    "AST-EVAL": ("CWE-94", "A03:2021-Injection", "medium"),
    "AST-SYNTAX": ("CWE-1164", "A04:2021-Insecure Design", "trivial"),
    "AST-BARE-EXCEPT": ("CWE-396", "A04:2021-Insecure Design", "trivial"),
    "AST-SWALLOWED": ("CWE-390", "A04:2021-Insecure Design", "trivial"),
    "AST-MUTABLE-DEFAULT": ("CWE-665", "A04:2021-Insecure Design", "trivial"),
    "AST-MANY-ARGS": ("CWE-1090", "A04:2021-Insecure Design", "low"),
    "AST-LONG-FUNCTION": ("CWE-1090", "A04:2021-Insecure Design", "medium"),
    "AST-SQLI": ("CWE-89", "A03:2021-Injection", "medium"),
    "AST-SHELL-TRUE": ("CWE-78", "A03:2021-Injection", "low"),
    "AST-UNSAFE-DESERIALIZATION": ("CWE-502", "A08:2021-Software and Data Integrity Failures", "medium"),
    "AST-REQUEST-NO-TIMEOUT": ("CWE-400", "A04:2021-Insecure Design", "trivial"),
    "AST-UNCLOSED-RESOURCE": ("CWE-775", "A04:2021-Insecure Design", "trivial"),

    # Bandit Rules
    "B101": ("CWE-703", "A04:2021-Insecure Design", "trivial"),      # assert used in production
    "B102": ("CWE-78", "A03:2021-Injection", "low"),                 # exec used
    "B307": ("CWE-94", "A03:2021-Injection", "medium"),              # eval used
    "B602": ("CWE-78", "A03:2021-Injection", "low"),                 # subprocess shell=True
    "B608": ("CWE-89", "A03:2021-Injection", "medium"),              # hardcoded SQL formatted query
    "B105": ("CWE-798", "A07:2021-Identification and Authentication Failures", "low"),  # hardcoded password
    "B106": ("CWE-798", "A07:2021-Identification and Authentication Failures", "low"),
    "B303": ("CWE-327", "A02:2021-Cryptographic Failures", "low"),    # MD5/SHA1
    "B311": ("CWE-330", "A02:2021-Cryptographic Failures", "trivial"),# pseudo-random in crypto
    "B506": ("CWE-502", "A08:2021-Software and Data Integrity Failures", "trivial"), # unsafe yaml.load

    # Pylint Rules
    "bare-except": ("CWE-396", "A04:2021-Insecure Design", "trivial"),
    "dangerous-default-value": ("CWE-665", "A04:2021-Insecure Design", "trivial"),
    "broad-exception-caught": ("CWE-396", "A04:2021-Insecure Design", "trivial"),
    "unused-import": ("CWE-561", "A04:2021-Insecure Design", "trivial"),
    "unused-variable": ("CWE-561", "A04:2021-Insecure Design", "trivial"),

    # Radon
    "CC": ("CWE-1090", "A04:2021-Insecure Design", "medium"),
    "MI": ("CWE-1090", "A04:2021-Insecure Design", "high"),
}

# Category fallbacks when rule_id is not mapped
CATEGORY_FALLBACKS: Dict[Category, Tuple[str, str, str]] = {
    Category.security: ("CWE-693", "A04:2021-Insecure Design", "medium"),
    Category.bug: ("CWE-691", "A04:2021-Insecure Design", "low"),
    Category.quality: ("CWE-1076", "A04:2021-Insecure Design", "trivial"),
    Category.refactor: ("CWE-1090", "A04:2021-Insecure Design", "medium"),
    Category.complexity: ("CWE-1090", "A04:2021-Insecure Design", "high"),
    Category.performance: ("CWE-400", "A04:2021-Insecure Design", "medium"),
    Category.style: ("CWE-1076", "A04:2021-Insecure Design", "trivial"),
}


def _estimate_blast_radius(finding: Finding) -> str:
    """Estimate impact blast radius: local, function, module, or system."""
    if finding.category == Category.security:
        if finding.severity in (Severity.critical, Severity.high):
            return "system"
        return "module"
    if finding.rule_id in ("AST-SYNTAX", "MI"):
        return "module"
    if finding.category in (Category.complexity, Category.refactor):
        return "function"
    return "local"


def enrich_finding_taxonomy(finding: Finding) -> Finding:
    """Enrich finding with CWE ID, OWASP category, remediation effort, and blast radius."""
    rule_key = finding.rule_id.strip() if finding.rule_id else ""
    
    if rule_key and rule_key in RULE_MAPPINGS:
        cwe, owasp, effort = RULE_MAPPINGS[rule_key]
    else:
        # Check rule substrings (e.g. bandit test IDs or names)
        matched = False
        for k, v in RULE_MAPPINGS.items():
            if k in rule_key or k.lower() in finding.title.lower():
                cwe, owasp, effort = v
                matched = True
                break
        if not matched:
            cwe, owasp, effort = CATEGORY_FALLBACKS.get(
                finding.category,
                ("CWE-691", "A04:2021-Insecure Design", "low"),
            )

    if not finding.cwe_id:
        finding.cwe_id = cwe
    if not finding.owasp_category:
        finding.owasp_category = owasp
    if not finding.remediation_effort:
        finding.remediation_effort = effort
    if not finding.blast_radius:
        finding.blast_radius = _estimate_blast_radius(finding)

    return finding
