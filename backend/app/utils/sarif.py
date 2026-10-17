"""OASIS Static Analysis Results Interchange Format (SARIF) v2.1.0 generator.

Enables native integration with GitHub Code Scanning alerts, SonarQube,
VS Code SARIF viewer, and enterprise CI/CD security pipelines.
"""
from typing import Any, Dict, List

from ..core.schemas import Finding, Severity, VerificationStatus



_SEVERITY_TO_SARIF_LEVEL = {
    Severity.critical: "error",
    Severity.high: "error",
    Severity.medium: "warning",
    Severity.low: "note",
    Severity.info: "none",
}


def to_sarif(findings: List[Finding], tool_name: str = "Agentic Code Review Framework",
             tool_version: str = "2.0.0") -> Dict[str, Any]:
    """Convert a list of findings to a valid SARIF v2.1.0 JSON object."""
    rules_map: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []

    for f in findings:
        # Exclude rejected findings from active SARIF alert reports
        if f.verification == VerificationStatus.rejected:
            continue

        rule_id = f.rule_id or f"AI-{f.category.value.upper()}"
        if rule_id not in rules_map:
            rule_entry: Dict[str, Any] = {
                "id": rule_id,
                "name": f.title[:60].replace(" ", "_"),
                "shortDescription": {"text": f.title},
                "fullDescription": {"text": f.description or f.title},
                "defaultConfiguration": {
                    "level": _SEVERITY_TO_SARIF_LEVEL.get(f.severity, "warning")
                },
                "properties": {
                    "category": f.category.value,
                    "precision": "high" if f.confidence >= 0.8 else "medium",
                }
            }
            if f.cwe_id:
                rule_entry["properties"]["cwe"] = [f.cwe_id]
            if f.owasp_category:
                rule_entry["properties"]["owasp"] = [f.owasp_category]
            rules_map[rule_id] = rule_entry

        result_entry: Dict[str, Any] = {
            "ruleId": rule_id,
            "level": _SEVERITY_TO_SARIF_LEVEL.get(f.severity, "warning"),
            "message": {
                "text": f"{f.title}\n\n{f.description}\n\nRecommendation: {f.recommendation}" if f.recommendation else f.title
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": f.file
                        },
                        "region": {
                            "startLine": max(1, f.line),
                            "endLine": max(f.line, f.end_line or f.line)
                        }
                    }
                }
            ],
            "properties": {
                "risk_score": f.risk_score,
                "confidence": f.confidence,
                "priority": f.priority,
                "verification": f.verification.value,
                "verification_reason": f.verification_reason,
                "sources": f.sources,
                "cwe": f.cwe_id,
                "owasp": f.owasp_category,
                "remediation_effort": f.remediation_effort,
                "blast_radius": f.blast_radius,
            }
        }
        results.append(result_entry)

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": tool_version,
                        "informationUri": "https://github.com/agentic-code-review/framework",
                        "rules": list(rules_map.values()),
                    }
                },
                "results": results
            }
        ]
    }
