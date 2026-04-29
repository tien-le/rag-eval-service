"""Redis-backed async job store for v1 (1K RPM).

Jobs are stored as JSON strings with a 1-hour TTL.
v2 production should replace this with a Postgres-backed store using the
async_jobs table defined in README-private.md § 10.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.infra.cache.redis_client import get_redis

JOB_TTL_SECONDS = 3600  # 1 hour; extend for long-running evals if needed
_KEY_PREFIX = "job:"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX}{job_id}"


async def create_job(job_type: str, idempotency_key: str | None = None) -> str:
    """Create a pending job entry and return its job_id."""
    job_id = str(uuid.uuid4())
    r = await get_redis()
    await r.set(
        _key(job_id),
        json.dumps(
            {
                "job_id": job_id,
                "job_type": job_type,
                "status": "pending",
                "idempotency_key": idempotency_key,
                "result": None,
                "error": None,
                "created_at": _now(),
                "started_at": None,
                "completed_at": None,
            }
        ),
        ex=JOB_TTL_SECONDS,
    )
    return job_id


async def get_job(job_id: str) -> dict | None:
    """Return job data dict or None if the job does not exist / has expired."""
    r = await get_redis()
    raw = await r.get(_key(job_id))
    return json.loads(raw) if raw else None


async def update_job(job_id: str, **fields: object) -> None:
    """Patch specific fields on an existing job (preserves TTL)."""
    r = await get_redis()
    raw = await r.get(_key(job_id))
    if not raw:
        return
    data = json.loads(raw)
    data.update(fields)
    # Reset TTL on every update so long-running jobs don't expire mid-flight
    await r.set(_key(job_id), json.dumps(data), ex=JOB_TTL_SECONDS)
