"""Tests for Enterprise Integrations, Quality Gates, SCA/SBOM, Compliance, and Streaming."""
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.schemas import (Category, Finding, QualityGatePolicy, ReviewResult,
                        ReviewSummary, Severity, VerificationStatus)


def test_integrations_list_and_test_endpoints():
    client = TestClient(app)

    # 1. List integrations
    resp = client.get("/api/v1/integrations")
    assert resp.status_code == 200
    data = resp.json()
    assert "integrations" in data
    assert len(data["integrations"]) >= 4

    # 2. Test Slack connector
    slack_resp = client.post("/api/v1/integrations/test", json={
        "integration_type": "slack",
        "channel_or_project": "#security-reviews"
    })
    assert slack_resp.status_code == 200
    slack_data = slack_resp.json()
    assert slack_data["status"] == "success"
    assert "blocks" in slack_data["generated_payload"]

    # 3. Test Jira connector
    jira_resp = client.post("/api/v1/integrations/test", json={
        "integration_type": "jira",
        "channel_or_project": "SEC"
    })
    assert jira_resp.status_code == 200
    jira_data = jira_resp.json()
    assert jira_data["status"] == "success"
    assert jira_data["generated_payload"]["fields"]["project"]["key"] == "SEC"

    # 4. Test Webhook with HMAC-SHA256 signature
    hook_resp = client.post("/api/v1/integrations/test", json={
        "integration_type": "webhook",
        "auth_token": "my-secret-key-123"
    })
    assert hook_resp.status_code == 200
    hook_data = hook_resp.json()
    assert hook_data["status"] == "success"
    assert hook_data["headers"]["X-CodeSentinel-Signature-256"].startswith("sha256=")

    # 5. Prometheus exporter
    prom_resp = client.get("/api/v1/integrations/metrics/prometheus")
    assert prom_resp.status_code == 200
    assert "text/plain" in prom_resp.headers["content-type"]
    assert "codesentinel_reviews_total" in prom_resp.text
    assert "codesentinel_risk_score_gauge" in prom_resp.text

    # 6. CI/CD SVG Status Badge
    badge_resp = client.get("/api/v1/badge/status.svg?label=CodeSentinel&message=A%2B%20pass&status=pass")
    assert badge_resp.status_code == 200
    assert "image/svg+xml" in badge_resp.headers["content-type"]
    assert "<svg" in badge_resp.text
    assert "CodeSentinel" in badge_resp.text
    assert "A+ pass" in badge_resp.text


def test_quality_gates_and_policy_engine():
    client = TestClient(app)

    # 1. Get default policy
    p_resp = client.get("/api/v1/policy/config")
    assert p_resp.status_code == 200
    policy = p_resp.json()
    assert policy["max_risk_score"] > 0
    assert policy["block_on_critical"] is True

    # 2. Evaluate passing review
    pass_summary = ReviewSummary(
        files_analyzed=1, total_findings=1, verified=1, rejected=0, uncertain=0,
        by_severity={"low": 1}, by_category={"quality": 1}, overall_risk=15.0,
        llm_used=False, posture_grade="A+"
    )
    pass_finding = Finding(
        file="app.py", line=10, category=Category.quality, severity=Severity.low,
        title="Docstring formatting", rule_id="QUAL-DOC-01", verification=VerificationStatus.verified
    )
    pass_result = ReviewResult(summary=pass_summary, findings=[pass_finding])

    eval_pass = client.post("/api/v1/policy/evaluate", json=pass_result.model_dump())
    assert eval_pass.status_code == 200
    pass_data = eval_pass.json()
    assert pass_data["status"] == "PASSED"
    assert pass_data["passed"] is True
    assert len(pass_data["violations"]) == 0

    # 3. Evaluate failing review with critical security flaw and secret
    fail_summary = ReviewSummary(
        files_analyzed=1, total_findings=2, verified=2, rejected=0, uncertain=0,
        by_severity={"critical": 1, "high": 1}, by_category={"security": 2}, overall_risk=82.0,
        llm_used=False, posture_grade="F"
    )
    fail_finding_1 = Finding(
        file="auth.py", line=5, category=Category.security, severity=Severity.critical,
        title="Unsafe eval injection", rule_id="AST-EVAL", cwe_id="CWE-94",
        verification=VerificationStatus.verified
    )
    fail_finding_2 = Finding(
        file="keys.py", line=1, category=Category.security, severity=Severity.high,
        title="Hardcoded AWS Access Key", rule_id="SEC-AWS-KEY", cwe_id="CWE-798",
        sources=["secret_scanner"], verification=VerificationStatus.verified
    )
    fail_result = ReviewResult(summary=fail_summary, findings=[fail_finding_1, fail_finding_2])

    eval_fail = client.post("/api/v1/policy/evaluate", json=fail_result.model_dump())
    assert eval_fail.status_code == 200
    fail_data = eval_fail.json()
    assert fail_data["status"] == "BLOCKED"
    assert fail_data["passed"] is False
    assert len(fail_data["violations"]) >= 2


def test_software_composition_analysis_and_sbom():
    client = TestClient(app)

    sample_requirements = """
# Insecure dependencies manifest
requests==2.28.1
cryptography==39.0.0
django==4.1.2
pyyaml==5.3
fastapi==0.110.0
"""
    # 1. Scan for CVEs
    scan_resp = client.post("/api/v1/sca/scan", json={
        "content": sample_requirements,
        "manifest_type": "requirements.txt"
    })
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["total_dependencies"] == 5
    assert scan_data["vulnerabilities_count"] >= 3
    cves = [f["cve_id"] for f in scan_data["findings"]]
    assert "CVE-2023-32681" in cves  # requests
    assert "CVE-2023-38325" in cves  # cryptography
    assert "CVE-2020-14343" in cves  # pyyaml

    # 2. Export CycloneDX v1.5 SBOM
    sbom_resp = client.post("/api/v1/sca/sbom", json={
        "content": sample_requirements,
        "manifest_type": "requirements.txt"
    })
    assert sbom_resp.status_code == 200
    sbom = sbom_resp.json()
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert len(sbom["components"]) == 5
    component_names = [c["name"] for c in sbom["components"]]
    assert "requests" in component_names
    assert "fastapi" in component_names


def test_compliance_scorecards():
    client = TestClient(app)

    findings = [
        Finding(
            file="db.py", line=12, category=Category.security, severity=Severity.critical,
            title="SQL Injection flaw", rule_id="SEC-SQLI", cwe_id="CWE-89",
            verification=VerificationStatus.verified
        ),
        Finding(
            file="auth.py", line=4, category=Category.security, severity=Severity.high,
            title="Hardcoded API token", rule_id="SEC-TOKEN", cwe_id="CWE-798",
            verification=VerificationStatus.verified
        )
    ]
    summary = ReviewSummary(
        files_analyzed=2, total_findings=2, verified=2, rejected=0, uncertain=0,
        by_severity={"critical": 1, "high": 1}, by_category={"security": 2}, overall_risk=65.0,
        llm_used=False, posture_grade="D"
    )
    review_result = ReviewResult(summary=summary, findings=findings)

    # 1. OWASP Top 10
    owasp_resp = client.post("/api/v1/compliance/scorecard?framework=OWASP_TOP_10", json=review_result.model_dump())
    assert owasp_resp.status_code == 200
    owasp_data = owasp_resp.json()
    assert "OWASP" in owasp_data["framework"]
    assert owasp_data["total_controls"] == 10
    # A03:2021 (Injection) should be NON_COMPLIANT due to CWE-89
    injection_ctrl = next(i for i in owasp_data["items"] if i["id"] == "A03:2021")
    assert injection_ctrl["status"] == "NON_COMPLIANT"
    assert injection_ctrl["finding_count"] >= 1

    # 2. SOC 2
    soc2_resp = client.post("/api/v1/compliance/scorecard?framework=SOC_2", json=review_result.model_dump())
    assert soc2_resp.status_code == 200
    soc2_data = soc2_resp.json()
    assert "SOC 2" in soc2_data["framework"]
    assert soc2_data["total_controls"] == 4


def test_realtime_review_sse_stream():
    client = TestClient(app)

    stream_resp = client.post("/api/v1/review/stream", json={
        "files": [{"path": "hello.py", "content": "print('hello world')\n"}]
    })
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    text = stream_resp.text
    assert "data: " in text
    assert "Static Analysis" in text
    assert "Review Finished" in text or "Complete" in text


def test_advanced_ui_routes():
    client = TestClient(app)
    routes = [
        "/integrations",
        "/policies",
        "/compliance",
        "/dependencies",
    ]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Route {r} returned {resp.status_code}"
        assert "<!DOCTYPE html>" in resp.text
        assert "CodeSentinel" in resp.text
