"""v2 jobs router — job status polling for Kafka-dispatched eval jobs (100K RPM).

GET /api/v2/jobs/{job_id}  → JobStatusResponse

Current storage: Redis (same TTL as v1 — 1 hour).
Production upgrade path: replace redis_job_store with a Postgres-backed store
using the async_jobs table (see README-private.md § 10) for durable, queryable
job history without TTL limits.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException

from app.api.deps.rate_limit import rate_limit_job_poll
from app.infra.jobs.redis_job_store import get_job
from app.schemas.job import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["v2 · Jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status_v2(
    job_id: str,
    rate_limit: Annotated[dict, rate_limit_job_poll],
) -> JobStatusResponse:
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail=f"Job '{job_id}' not found or expired"
        )
    return JobStatusResponse(**job)
