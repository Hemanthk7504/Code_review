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


async def run_job(job_id: str, work: Callable[[], Awaitable[dict]]) -> None:
    job = _JOBS[job_id]
    job.status = "running"
    try:
        job.result = await work()
        job.status = "done"
    except Exception as exc:  # report the failure through the job record
        log.exception("job %s failed", job_id)
        job.status, job.detail = "failed", str(exc)
