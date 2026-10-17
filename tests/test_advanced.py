"""Tests for advanced features: Secret Scanner, Advanced AST Rules, CWE Taxonomy, SARIF Export, Posture Grading, and Web Dashboard."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cwe_mapping import enrich_finding_taxonomy
from app.main import app
from app.risk import calculate_posture_grade, extract_top_risks, summarize_cwe_counts
from app.sarif import to_sarif
from app.schemas import Category, FileInput, Finding, Severity, VerificationStatus
from app.secret_scanner import scan_secrets
from app.static_analysis import analyze_file_sync


def test_secret_scanner_detects_credentials():
    code = '''
AWS_KEY = "AKIA1234567890ABCDEF"
OPENAI = "sk-1234567890abcdef1234567890abcdef"
DUMMY = "your-api-key-here"  # placeholder should be ignored
'''
    findings = scan_secrets("config.py", code)
    assert len(findings) == 2
    rule_ids = {f.rule_id for f in findings}
    assert "SEC-AWS-KEY" in rule_ids
    assert "SEC-OPENAI-KEY" in rule_ids
    # Secrets should be redacted in code snippet
    for f in findings:
        assert "AKIAIOSFODNN7EXAMPLE" not in f.code_snippet
        assert f.cwe_id == "CWE-798"
        assert f.verification == VerificationStatus.pending


def test_advanced_ast_sqli_and_shell_true():
    code = '''
import subprocess
import sqlite3

def dangerous_function(user_input, cmd):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM accounts WHERE id = '{user_input}'")
    subprocess.run(cmd, shell=True)
'''
    findings = analyze_file_sync("vuln.py", code)
    rule_ids = {f.rule_id for f in findings}
    assert "AST-SQLI" in rule_ids
    assert "AST-SHELL-TRUE" in rule_ids

    sqli = next(f for f in findings if f.rule_id == "AST-SQLI")
    assert sqli.cwe_id == "CWE-89"
    assert sqli.category == Category.security
    assert sqli.severity == Severity.high


def test_advanced_ast_pickle_and_request_timeout():
    code = '''
import pickle
import requests

def fetch_and_load(raw_data, url):
    obj = pickle.loads(raw_data)
    resp = requests.get(url)
    return obj, resp
'''
    findings = analyze_file_sync("api.py", code)
    rule_ids = {f.rule_id for f in findings}
    assert "AST-UNSAFE-DESERIALIZATION" in rule_ids
    assert "AST-REQUEST-NO-TIMEOUT" in rule_ids

    pickle_f = next(f for f in findings if f.rule_id == "AST-UNSAFE-DESERIALIZATION")
    assert pickle_f.severity == Severity.critical
    assert pickle_f.cwe_id == "CWE-502"


def test_cwe_taxonomy_enrichment():
    f = Finding(
        file="app.py",
        line=10,
        category=Category.security,
        severity=Severity.high,
        title="SQL injection found",
        rule_id="B608",
        sources=["bandit"]
    )
    enrich_finding_taxonomy(f)
    assert f.cwe_id == "CWE-89"
    assert "Injection" in f.owasp_category
    assert f.remediation_effort == "medium"
    assert f.blast_radius in ("system", "module")


def test_posture_grading_and_top_risks():
    assert calculate_posture_grade(10.0) == "A+"
    assert calculate_posture_grade(25.0) == "A"
    assert calculate_posture_grade(45.0) == "B"
    assert calculate_posture_grade(65.0) == "C"
    assert calculate_posture_grade(80.0) == "D"
    assert calculate_posture_grade(95.0) == "F"

    f1 = Finding(file="a.py", line=1, category=Category.security, severity=Severity.critical,
                 title="Hardcoded Key", rule_id="SEC-AWS-KEY", cwe_id="CWE-798", risk_score=85.0, priority="critical")
    f2 = Finding(file="a.py", line=10, category=Category.bug, severity=Severity.low,
                 title="Typo", rule_id="TYPO", risk_score=15.0, priority="low")
    
    top = extract_top_risks([f1, f2], limit=1)
    assert len(top) == 1
    assert "CRITICAL" in top[0] and "CWE-798" in top[0]

    cwe_map = summarize_cwe_counts([f1, f2])
    assert cwe_map.get("CWE-798") == 1


def test_sarif_export():
    finding = Finding(
        file="src/auth.py",
        line=25,
        end_line=27,
        category=Category.security,
        severity=Severity.high,
        title="Unsafe eval execution",
        description="Arbitrary code execution risk.",
        rule_id="AST-EVAL",
        cwe_id="CWE-94",
        sources=["ast"],
        confidence=0.9,
        risk_score=78.5,
        verification=VerificationStatus.verified,
    )
    sarif = to_sarif([finding])
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Agentic Code Review Framework"
    assert len(run["results"]) == 1
    res = run["results"][0]
    assert res["ruleId"] == "AST-EVAL"
    assert res["level"] == "error"
    assert res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/auth.py"
    assert res["locations"][0]["physicalLocation"]["region"]["startLine"] == 25


def test_advanced_api_endpoints():
    client = TestClient(app)
    
    # 1. Dashboard HTML
    dash_resp = client.get("/dashboard")
    assert dash_resp.status_code == 200
    assert "CodeSentinel" in dash_resp.text
    assert "Agentic Code Review" in dash_resp.text
    assert "<!DOCTYPE html>" in dash_resp.text

    # 2. Metrics endpoint
    metrics_resp = client.get("/api/v1/metrics")
    assert metrics_resp.status_code == 200
    m = metrics_resp.json()
    assert "bug_detection" in m["registered_agents"]
    assert "performance" in m["registered_agents"]
    assert "secret_scanner" in m["static_tools"]
    assert m["max_fix_retries"] >= 2

    # 3. Quick audit endpoint
    audit_resp = client.post("/api/v1/audit/quick", json={
        "code": "def f():\n    eval('1+1')\n",
        "filename": "calc.py"
    })
    assert audit_resp.status_code == 200
    body = audit_resp.json()
    assert body["summary"]["files_analyzed"] == 1
    assert any("eval" in f["title"].lower() for f in body["findings"])

    # 4. SARIF export endpoint
    f_dict = {
        "file": "test.py",
        "line": 5,
        "category": "security",
        "severity": "high",
        "title": "SQL Injection",
        "rule_id": "AST-SQLI",
        "sources": ["ast"],
        "confidence": 0.9,
        "verification": "verified"
    }
    sarif_resp = client.post("/api/v1/export/sarif", json={"findings": [f_dict]})
    assert sarif_resp.status_code == 200
    sarif_data = sarif_resp.json()
    assert sarif_data["version"] == "2.1.0"
    assert len(sarif_data["runs"][0]["results"]) == 1
