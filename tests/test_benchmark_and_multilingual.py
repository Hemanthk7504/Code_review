"""Unit and integration tests for Evidence-Based Verification, Multilingual Engine, and Held-Out Benchmark."""
import pytest
from fastapi.testclient import TestClient

from backend.app.benchmark.dataset import BENCHMARK_DATASET, BenchmarkCase
from backend.app.benchmark.evaluator import run_benchmark_evaluation
from backend.app.engine.language import Language, detect_language
from backend.app.main import app
from backend.app.services.github_client import parse_repo_and_pr


client = TestClient(app)


@pytest.mark.asyncio
async def test_benchmark_precision_target_met():
    """Empirically evaluate the held-out labelled benchmark and prove >= 95% precision."""
    res = await run_benchmark_evaluation(evaluate_remediation=False)

    assert res.total_cases >= 20
    assert res.target_precision_met is True
    # Assert precision is at least 95% (0.95)
    assert res.precision >= 0.95, f"Expected precision >= 0.95, got {res.precision}"
    # Assert recall is useful
    assert res.recall >= 0.90, f"Expected recall >= 0.90, got {res.recall}"
    # Assert false positive rate is low
    assert res.false_positive_rate <= 0.05, f"Expected FPR <= 0.05, got {res.false_positive_rate}"

    # Verify language-specific metrics exist
    for lang in ["python", "javascript", "go", "java"]:
        assert lang in res.by_language
        assert res.by_language[lang].precision >= 0.95


def test_multilingual_language_detection():
    """Verify automatic language identification and classification."""
    assert detect_language("app.py").language == Language.PYTHON
    assert detect_language("frontend/index.ts").language == Language.TYPESCRIPT
    assert detect_language("service/main.go").language == Language.GO
    assert detect_language("App.java").language == Language.JAVA
    assert detect_language("core.cpp").language == Language.C_CPP
    assert detect_language("photo.png").language == Language.BINARY
    assert detect_language("photo.png").is_supported is False
    assert detect_language("document.docx").is_supported is False
    assert detect_language("script.unknownxyz").is_supported is False


def test_universal_repo_and_pr_parser():
    """Verify URL parsing for full PR URLs, repo URLs, SSH, and short forms."""
    # Full PR URL
    repo, pr = parse_repo_and_pr("https://github.com/pallets/flask/pull/5012")
    assert repo == "pallets/flask"
    assert pr == 5012

    # Full repo URL with explicit PR
    repo, pr = parse_repo_and_pr("https://github.com/octocat/Hello-World", 42)
    assert repo == "octocat/Hello-World"
    assert pr == 42

    # Plain owner/repo with explicit PR
    repo, pr = parse_repo_and_pr("torvalds/linux", 100)
    assert repo == "torvalds/linux"
    assert pr == 100

    # SSH format with explicit PR
    repo, pr = parse_repo_and_pr("git@github.com:facebook/react.git", 77)
    assert repo == "facebook/react"
    assert pr == 77

    # Missing PR error
    with pytest.raises(ValueError):
        parse_repo_and_pr("https://github.com/pallets/flask")


def test_analytics_metrics_api_endpoint():
    """Verify that /api/v1/analytics/metrics returns real empirical evaluation data."""
    resp = client.get("/api/v1/analytics/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "benchmark" in data
    assert "telemetry" in data

    bench = data["benchmark"]
    assert bench["precision_percent"] >= 95.0
    assert bench["target_precision_met"] is True
    assert "by_language" in bench
    assert "python" in bench["by_language"]
    assert "javascript" in bench["by_language"]
