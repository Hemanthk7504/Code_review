"""Tiny in-memory job store for background GitHub runs."""
import logging
from typing import Awaitable, Callable
from uuid import uuid4

from ..core.schemas import JobInfo


log = logging.getLogger(__name__)
_JOBS: dict[str, JobInfo] = {}


def create_job() -> JobInfo:
    job = JobInfo(job_id=uuid4().hex[:12], status="queued")
    _JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> JobInfo | None:
    return _JOBS.get(job_id)


def update_job_progress(job_id: str, stage: str, progress: int, log_message: str | None = None) -> None:
    job = _JOBS.get(job_id)
    if job:
        job.current_stage = stage
        job.progress = max(0, min(100, progress))
        if log_message:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            job.logs.append(f"[{timestamp}] {log_message}")
            job.detail = log_message


async def run_job(job_id: str, work: Callable[[], Awaitable[dict]]) -> None:
    job = _JOBS[job_id]
    job.status = "running"
    update_job_progress(job_id, "Initialized", 5, "Job queued and dispatched to background pipeline.")
    try:
        job.result = await work()
        job.status = "done"
        update_job_progress(job_id, "Complete", 100, "Background processing completed successfully.")
    except Exception as exc:  # report the failure through the job record
        log.exception("job %s failed", job_id)
        job.status, job.detail = "failed", str(exc)
        update_job_progress(job_id, "Failed", job.progress, f"Error: {exc}")
