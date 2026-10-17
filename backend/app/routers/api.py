"""HTTP endpoints."""
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

from ..services import jobs
from ..core.config import get_settings
from ..engine.llm import llm_client
from ..engine.pipeline import process_pull_request, review_and_revise, review_files
from ..core.schemas import (ComplianceScorecardRequest, ComplianceScorecardResult, DependencyScanRequest, DependencyScanResult,
                      FileInput, FullResult, IntegrationConfig, IntegrationTestRequest,
                      JobInfo, PolicyEvaluationRequest, PolicyEvaluationResult, PullRequestRequest, QualityGatePolicy,
                      QuickAuditRequest, ReviewRequest, ReviewResult, SarifExportRequest)
from ..utils.security import require_api_key, verify_github_signature



router = APIRouter(prefix="/api/v1")
protected = [Depends(require_api_key)]


@router.get("/health")
async def health():
    s = get_settings()
    return {"status": "ok", "app": s.app_name, "llm_enabled": llm_client.enabled,
            "github_token_set": bool(s.github_token)}


@router.post("/review", response_model=ReviewResult, dependencies=protected)
async def review(req: ReviewRequest):
    """Analyse code: static + AI analysis, risk scoring and self-verification."""
    if not req.files:
        raise HTTPException(400, "Send at least one file.")
    result = await review_files(req.files)
    try:
        from ..db.session import SessionLocal
        from ..models.review import ReviewRecordModel
        target_path = req.files[0].path if req.files else "code_review"
        with SessionLocal() as db:
            rec = ReviewRecordModel(
                target_path=target_path,
                files_analyzed=len(req.files),
                total_findings=len(result.findings),
                verified_findings=len(result.findings),
                overall_risk=result.overall_risk,
                posture_grade=result.posture_grade,
                findings_json=json.dumps([f.model_dump() for f in result.findings]),
            )
            db.add(rec)
            db.commit()
    except Exception:
        pass
    return result



@router.post("/review/upload", response_model=ReviewResult, dependencies=protected)
async def review_upload(files: list[UploadFile] = File(...)):
    items = [FileInput(path=f.filename or "upload.py", content=(await f.read()).decode("utf-8", "replace"))
             for f in files]
    return await review_files(items)


@router.post("/revise", response_model=FullResult, dependencies=protected)
async def revise(req: ReviewRequest):
    """Full loop without GitHub: review, generate fixes, re-validate, return diffs."""
    if not req.files:
        raise HTTPException(400, "Send at least one file.")
    return await review_and_revise(req.files)


def _queue(background: BackgroundTasks, repo: str, number: int, token: Optional[str], create_pr: bool) -> JobInfo:
    job = jobs.create_job()
    background.add_task(jobs.run_job, job.job_id,
                        lambda: process_pull_request(repo, number, token, create_pr))
    return job


@router.post("/github/pull-request", response_model=JobInfo, dependencies=protected)
async def github_pull_request(req: PullRequestRequest, background: BackgroundTasks):
    """Called by the GitHub Action. Returns a job id right away; the work runs in the background."""
    return _queue(background, req.repo, req.pr_number, req.github_token, req.create_revision_pr)


@router.post("/github/webhook")
async def github_webhook(request: Request, background: BackgroundTasks,
                         x_github_event: Optional[str] = Header(default=None),
                         x_hub_signature_256: Optional[str] = Header(default=None)):
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(401, "Bad webhook signature.")
    if x_github_event != "pull_request":
        return {"ignored": x_github_event}
    payload = json.loads(body)
    if payload.get("action") not in {"opened", "synchronize", "reopened"}:
        return {"ignored": payload.get("action")}
    job = _queue(background, payload["repository"]["full_name"], payload["number"], None, True)
    return {"job_id": job.job_id}


@router.get("/jobs/{job_id}", response_model=JobInfo, dependencies=protected)
async def job_status(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Unknown job id.")
    return job


@router.post("/export/sarif")
async def export_sarif_endpoint(req: SarifExportRequest):
    """Export review findings to OASIS SARIF v2.1.0 format for GitHub Code Scanning."""
    from ..utils.sarif import to_sarif
    return to_sarif(req.findings)


@router.post("/export/markdown")
async def export_markdown_endpoint(req: ReviewRequest):
    """Generate a clean Markdown audit report."""
    from ..utils.report import review_comment
    review_res = await review_files(req.files)
    return {"markdown": review_comment(review_res)}



@router.post("/audit/quick", response_model=ReviewResult)
async def audit_quick(req: QuickAuditRequest):
    """Fast single-file code audit for interactive playgrounds."""
    file_input = FileInput(path=req.filename, content=req.code)
    return await review_files([file_input])


@router.get("/metrics")
async def engine_metrics():
    """Report engine configuration, active agents, and static capabilities."""
    s = get_settings()
    from ..engine.agents import AGENTS
    from ..core.schemas import STATIC_TOOLS

    return {
        "app": s.app_name,
        "registered_agents": list(AGENTS.keys()),
        "static_tools": list(STATIC_TOOLS),
        "llm_ready": s.llm_ready,
        "max_fix_retries": s.max_fix_retries,
        "generate_unit_tests": s.generate_unit_tests,
        "secrets_scanner": s.enable_secrets_scanner,
        "cwe_mapping": s.enable_cwe_mapping,
    }


@router.get("/reviews/history")
async def get_review_history():
    """Retrieve persisted review history from SQLite database."""
    try:
        from ..db.session import SessionLocal
        from ..models.review import ReviewRecordModel
        with SessionLocal() as db:
            records = db.query(ReviewRecordModel).order_by(ReviewRecordModel.created_at.desc()).limit(50).all()
            return [
                {
                    "id": r.id,
                    "target_path": r.target_path,
                    "files_analyzed": r.files_analyzed,
                    "total_findings": r.total_findings,
                    "verified_findings": r.verified_findings,
                    "overall_risk": r.overall_risk,
                    "posture_grade": r.posture_grade,
                    "created_at": r.created_at,
                }
                for r in records
            ]
    except Exception:
        return []


@router.get("/audit-logs")
async def get_audit_logs():
    """Retrieve persisted audit events from SQLite database."""
    try:
        from ..db.session import SessionLocal
        from ..models.audit import AuditLogModel
        with SessionLocal() as db:
            logs = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(50).all()
            return [
                {
                    "id": l.id,
                    "action": l.action,
                    "username": l.username,
                    "details": l.details,
                    "ip_address": l.ip_address,
                    "timestamp": l.timestamp,
                }
                for l in logs
            ]
    except Exception:
        return []


# =========================================================================

# ADVANCED ENTERPRISE INTEGRATIONS & COMPLIANCE ENDPOINTS
# =========================================================================

@router.get("/integrations")
async def get_integrations_list():
    """Retrieve all configured ChatOps, SCM, Issue Tracker, and SIEM integrations."""
    from ..integrations.dispatcher import list_integrations
    return {"integrations": list_integrations()}


@router.post("/integrations/config")
async def save_integration_config(config: IntegrationConfig):
    """Save or update an integration connector."""
    from ..integrations.dispatcher import update_integration
    return {"status": "saved", "integration": update_integration(config)}


@router.post("/integrations/test")
async def test_integration_endpoint(req: IntegrationTestRequest):
    """Perform a live handshake or payload verification test with a third-party service."""
    from ..integrations.dispatcher import test_integration_connection
    return test_integration_connection(req)


@router.get("/integrations/metrics/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Export CodeSentinel telemetry in OpenMetrics / Prometheus exposition format."""
    from ..integrations.dispatcher import generate_prometheus_metrics
    return PlainTextResponse(generate_prometheus_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/badge/status.svg")
async def badge_svg(label: str = "security", message: str = "A+ pass", status: str = "pass"):
    """Dynamic SVG badge for CI/CD pipelines and README repository headers."""
    from ..integrations.dispatcher import generate_badge_svg
    svg = generate_badge_svg(label=label, message=message, status=status)
    return Response(content=svg, media_type="image/svg+xml")


# ---------- Quality Gates & Policy Engine ----------
@router.get("/policy/config", response_model=QualityGatePolicy)
async def get_policy_config():
    """Retrieve currently active enterprise Quality Gate policy."""
    from ..services.policy_engine import get_active_policy
    return get_active_policy()


@router.post("/policy/config", response_model=QualityGatePolicy)
async def update_policy_config(policy: QualityGatePolicy):
    """Update active enterprise Quality Gate policy thresholds."""
    from ..services.policy_engine import set_active_policy
    return set_active_policy(policy)


@router.post("/policy/evaluate", response_model=PolicyEvaluationResult)
async def evaluate_policy_endpoint(req: PolicyEvaluationRequest):
    """Evaluate review findings against enterprise quality gate rules."""
    from ..services.policy_engine import evaluate_quality_gate
    return evaluate_quality_gate(req)


# ---------- Software Composition Analysis (SCA) & SBOM ----------
@router.post("/sca/scan", response_model=DependencyScanResult)
async def sca_scan_endpoint(req: DependencyScanRequest):
    """Scan software dependency manifest for known CVEs and insecure versions."""
    from ..scanners.sca import scan_dependencies
    return scan_dependencies(req.content, req.manifest_type)


@router.post("/sca/sbom")
async def sca_sbom_endpoint(req: DependencyScanRequest):
    """Generate CycloneDX v1.5 JSON Software Bill of Materials (SBOM)."""
    from ..scanners.sca import generate_cyclonedx_sbom
    return generate_cyclonedx_sbom(req.content)


# ---------- Regulatory Compliance Scorecards ----------
@router.post("/compliance/scorecard", response_model=ComplianceScorecardResult)
async def compliance_scorecard_endpoint(req: ComplianceScorecardRequest, framework: str = "OWASP_TOP_10"):
    """Calculate compliance posture against OWASP Top 10, SOC 2, or PCI-DSS."""
    from ..services.compliance import generate_compliance_scorecard
    return generate_compliance_scorecard(req.findings, framework)



# ---------- Real-time Review Event Streaming (SSE) ----------
@router.post("/review/stream")
async def review_stream_endpoint(req: ReviewRequest):
    """Server-Sent Events (SSE) streaming endpoint for real-time review progress."""
    import asyncio
    async def event_generator():
        yield f"data: {json.dumps({'stage': 1, 'name': 'Static Analysis', 'status': 'running', 'detail': 'Running Bandit, Pylint, Radon, AST & Secrets Scanner'})}\n\n"
        await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'stage': 2, 'name': 'AI Specialist Agents', 'status': 'running', 'detail': 'Dispatching security, bug, quality, performance & architecture agents'})}\n\n"
        await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'stage': 3, 'name': 'Consolidation', 'status': 'running', 'detail': 'Deduplicating findings across AST and agent outputs'})}\n\n"
        # Run review
        res = await review_files(req.files)
        yield f"data: {json.dumps({'stage': 5, 'name': 'Self-Verification', 'status': 'running', 'detail': 'Auditing findings for hallucinations'})}\n\n"
        await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'stage': 7, 'name': 'Complete', 'status': 'done', 'result': res.model_dump()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

