"""Tests run without a real LLM. A fake LLM is plugged in to test the full loop."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import llm as llm_module  # noqa: E402
from app.consolidation import consolidate  # noqa: E402
from app.github_client import changed_lines_from_patch  # noqa: E402
from app.main import app  # noqa: E402
from app.pipeline import review_and_revise, review_files  # noqa: E402
from app.risk import apply_risk, overall_risk  # noqa: E402
from app.schemas import (Category, FileInput, Finding, Severity,  # noqa: E402
                         VerificationStatus)

BAD_CODE = '''def total(values, cache={}):
    try:
        result = eval(values)
    except:
        pass
    return result
'''

GOOD_CODE = '''import ast
import logging


def total(values, cache=None):
    if cache is None:
        cache = {}
    result = 0
    try:
        result = ast.literal_eval(values)
    except (ValueError, SyntaxError):
        logging.exception("bad input")
    return result
'''


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def no_llm(monkeypatch):
    monkeypatch.setattr(type(llm_module.llm_client), "enabled", property(lambda self: False))


@pytest.fixture
def fake_llm(monkeypatch):
    async def fake_chat_json(self, system, user, *, task="", max_tokens=4096):
        if task == "agent:bug_detection" and "eval(values)" in user:
            return {"findings": [
                {"line": 3, "severity": "high", "title": "Unsafe eval of input", "description": "eval on user data",
                 "recommendation": "use ast.literal_eval", "code_snippet": "result = eval(values)", "confidence": 0.9},
                {"line": 999, "severity": "high", "title": "Made-up issue", "description": "does not exist",
                 "recommendation": "n/a", "code_snippet": "nothing here", "confidence": 0.9},
                {"line": 5, "severity": "medium", "title": "Invented problem with wrong code", "description": "x",
                 "recommendation": "y", "code_snippet": "this text is not in the file", "confidence": 0.9},
            ]}
        if task.startswith("agent:"):
            return {"findings": []}
        if task == "verify":
            return {"verdict": "confirmed", "confidence": 0.95, "reason": "code shows it"}
        if task == "fix":
            return {"revised_code": GOOD_CODE, "changes": [
                {"finding_id": fid, "problem": "p", "modification": "m"}
                for fid in __import__("re").findall(r"id=(\w+)", user)]}
        return None

    monkeypatch.setattr(type(llm_module.llm_client), "enabled", property(lambda self: True))
    monkeypatch.setattr(type(llm_module.llm_client), "chat_json", fake_chat_json)


def test_extract_json():
    assert llm_module.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm_module.extract_json('Sure! {"a": [1, 2]} done') == {"a": [1, 2]}
    assert llm_module.extract_json("no json") is None


def test_changed_lines_from_patch():
    patch = "@@ -1,3 +1,4 @@\n a\n+b\n c\n-d\n+e"
    assert changed_lines_from_patch(patch) == [2, 4]


def test_consolidation_merges_static_and_ai():
    a = Finding(file="x.py", line=10, category=Category.security, severity=Severity.medium,
                title="eval used", sources=["bandit"], confidence=0.7, rule_id="B307")
    b = Finding(file="x.py", line=11, category=Category.security, severity=Severity.high,
                title="Unsafe eval", sources=["security_analysis"], confidence=0.6)
    far = Finding(file="x.py", line=80, category=Category.security, severity=Severity.low,
                  title="other", sources=["security_analysis"], confidence=0.5)
    merged = consolidate([a, b, far])
    assert len(merged) == 2
    top = next(m for m in merged if m.line in (10, 11))
    assert top.severity == Severity.high
    assert set(top.sources) == {"bandit", "security_analysis"}
    assert top.confidence > 0.7


def test_risk_orders_security_above_style():
    sec = Finding(file="x.py", line=1, category=Category.security, severity=Severity.high,
                  title="s", sources=["bandit"], confidence=0.9)
    sty = Finding(file="x.py", line=2, category=Category.style, severity=Severity.low,
                  title="t", sources=["pylint"], confidence=0.9)
    out = apply_risk([sty, sec], [FileInput(path="x.py", content="a\nb\n")])
    assert out[0] is sec and sec.risk_score > sty.risk_score
    sec.verification = VerificationStatus.rejected
    sty.verification = VerificationStatus.rejected
    assert overall_risk(out) == 0


def test_static_review_without_llm(no_llm):
    result = run(review_files([FileInput(path="bad.py", content=BAD_CODE),
                               FileInput(path="README.md", content="# hi")]))
    assert result.skipped_files == ["README.md"]
    sources = {s for f in result.findings for s in f.sources}
    assert {"ast", "pylint", "bandit"} <= sources
    # on the 'except:' line the AST check reports two different issues (bare except, swallowed error);
    # pylint's bare-except duplicate is merged into the bare-except one, not into the swallowed one
    at_except = [f for f in result.findings if f.line == 4 and f.category == Category.bug]
    assert len(at_except) == 2
    assert sum(1 for f in at_except if {"ast", "pylint"} <= set(f.sources)) == 1
    assert any({"ast", "bandit"} <= set(f.sources) for f in result.findings)  # eval(): AST + Bandit merged
    assert all(f.verification == VerificationStatus.verified for f in result.findings)
    assert result.summary.overall_risk > 0 and not result.summary.llm_used


def test_syntax_error_is_reported(no_llm):
    result = run(review_files([FileInput(path="broken.py", content="def f(:\n    pass\n")]))
    assert result.findings[0].rule_id == "AST-SYNTAX"


def test_full_loop_with_fake_llm(fake_llm):
    full = run(review_and_revise([FileInput(path="bad.py", content=BAD_CODE)]))
    by_title = {f.title: f for f in full.review.findings}
    # AI claim with a non-existent line is rejected; wrong snippet without static support is rejected/uncertain
    assert by_title["Made-up issue"].verification == VerificationStatus.rejected
    assert by_title["Invented problem with wrong code"].verification != VerificationStatus.verified
    # the real eval issue is corroborated by static analysis and AI
    eval_f = next(f for f in full.review.findings if "eval" in f.title.lower() and f.line == 3)
    assert eval_f.verification == VerificationStatus.verified
    assert eval_f.static_sources and eval_f.ai_sources
    # fix + re-validation
    assert len(full.revisions) == 1
    out = full.revisions[0]
    assert out.revision.syntax_ok and "ast.literal_eval" in out.revision.diff
    v = out.validation
    assert v.accepted, v.reasons
    assert v.risk_after < v.risk_before and v.resolution_ratio == 1.0 and not v.new_findings


def test_bad_revision_is_rejected(monkeypatch, fake_llm):
    async def fake_fix_bad(self, system, user, *, task="", max_tokens=4096):
        if task == "fix":
            return {"revised_code": BAD_CODE.replace("result = eval(values)", "result = eval(values)  # kept"),
                    "changes": []}
        return await orig(self, system, user, task=task, max_tokens=max_tokens)

    orig = type(llm_module.llm_client).chat_json
    monkeypatch.setattr(type(llm_module.llm_client), "chat_json", fake_fix_bad)
    full = run(review_and_revise([FileInput(path="bad.py", content=BAD_CODE)]))
    assert full.revisions and not full.revisions[0].validation.accepted


def test_api_endpoints(no_llm):
    client = TestClient(app)
    assert client.get("/api/v1/health").json()["status"] == "ok"
    r = client.post("/api/v1/review", json={"files": [{"path": "bad.py", "content": BAD_CODE}]})
    assert r.status_code == 200 and r.json()["summary"]["total_findings"] > 0
    r = client.post("/api/v1/revise", json={"files": [{"path": "bad.py", "content": BAD_CODE}]})
    assert r.status_code == 200 and r.json()["revisions"] == []
    assert client.post("/api/v1/review", json={"files": []}).status_code == 400
    assert client.get("/api/v1/jobs/nope").status_code == 404


def test_api_key_is_enforced(monkeypatch, no_llm):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "api_key", "secret")
    client = TestClient(app)
    body = {"files": [{"path": "a.py", "content": "x = 1\n"}]}
    assert client.post("/api/v1/review", json=body).status_code == 401
    assert client.post("/api/v1/review", json=body, headers={"X-API-Key": "secret"}).status_code == 200


def test_webhook_signature(monkeypatch):
    import hashlib
    import hmac
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "github_webhook_secret", "s3")
    client = TestClient(app)
    body = b'{"action": "closed"}'
    assert client.post("/api/v1/github/webhook", content=body,
                       headers={"X-GitHub-Event": "pull_request"}).status_code == 401
    sig = "sha256=" + hmac.new(b"s3", body, hashlib.sha256).hexdigest()
    r = client.post("/api/v1/github/webhook", content=body,
                    headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": sig})
    assert r.status_code == 200 and r.json() == {"ignored": "closed"}
