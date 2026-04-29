"""Job lifecycle schemas shared between v1 (Celery/Redis) and v2 (Kafka/Postgres)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class AsyncJobResponse(BaseModel):
    """Returned immediately when an async job is enqueued."""

    job_id: str
    status: Literal["pending"] = "pending"
    message: str = "Job enqueued. Poll /jobs/{job_id} for status."


class JobStatusResponse(BaseModel):
    """Returned by GET /v1/jobs/{job_id} or GET /v2/jobs/{job_id}."""

    job_id: str
    job_type: str
    status: Literal["pending", "running", "completed", "failed"]
    result: dict[str, Any] | None = None
    error: str | None = None
    idempotency_key: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
