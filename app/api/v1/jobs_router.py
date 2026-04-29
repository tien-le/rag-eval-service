"""v1 jobs router — Redis-backed job status polling (1K RPM).

GET /api/v1/jobs/{job_id}  → JobStatusResponse

Job entries expire after 1 hour (JOB_TTL_SECONDS in redis_job_store).
For longer retention, migrate to the async_jobs Postgres table (see README § 10).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.infra.jobs.redis_job_store import get_job
from app.schemas.job import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["v1 · Jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or expired")
    return JobStatusResponse(**job)
