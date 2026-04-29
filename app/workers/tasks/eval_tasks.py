"""Celery eval tasks for v1 async evaluation (1K RPM, Redis broker).

Each task:
  1. Updates job status in Redis (running → completed/failed).
  2. Runs the evaluation via EvaluationService.
  3. Retries up to max_retries times on transient failures.

All imports that touch LLM/model objects are deferred inside the task body to
speed up worker startup and avoid circular imports.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# RAG single-turn eval
# ---------------------------------------------------------------------------


@celery_app.task(
    name="eval.ragas_single_turn",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="evaluation",
)
def ragas_single_turn_task(self, job_id: str, payload: dict) -> dict:
    from app.infra.jobs.redis_job_store import update_job
    from app.infra.llm_gateways.ollama_provider import (
        evaluator_embeddings,
        evaluator_model,
    )
    from app.services.evaluation_service import EvaluationService

    async def _eval() -> dict:
        await update_job(job_id, status="running", started_at=_now())
        svc = EvaluationService(
            evaluator_llm=evaluator_model,
            evaluator_embeddings=evaluator_embeddings,
        )
        try:
            result = await svc.evaluate_ragas_single_turn(**payload)
            await update_job(
                job_id, status="completed", result=result, completed_at=_now()
            )
            return result
        except Exception as exc:
            await update_job(
                job_id, status="failed", error=str(exc), completed_at=_now()
            )
            raise

    try:
        return _run_async(_eval())
    except Exception as exc:
        logger.exception("eval.ragas_single_turn job=%s failed: %s", job_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# RAG multi-turn eval
# ---------------------------------------------------------------------------


@celery_app.task(
    name="eval.ragas_multi_turn",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="evaluation",
)
def ragas_multi_turn_task(self, job_id: str, payload: dict) -> dict:
    from app.infra.jobs.redis_job_store import update_job
    from app.infra.llm_gateways.ollama_provider import (
        evaluator_embeddings,
        evaluator_model,
    )
    from app.services.evaluation_service import EvaluationService

    async def _eval() -> dict:
        await update_job(job_id, status="running", started_at=_now())
        svc = EvaluationService(
            evaluator_llm=evaluator_model,
            evaluator_embeddings=evaluator_embeddings,
        )
        try:
            result = await svc.evaluate_ragas_multi_turn(**payload)
            await update_job(
                job_id, status="completed", result=result, completed_at=_now()
            )
            return result
        except Exception as exc:
            await update_job(
                job_id, status="failed", error=str(exc), completed_at=_now()
            )
            raise

    try:
        return _run_async(_eval())
    except Exception as exc:
        logger.exception("eval.ragas_multi_turn job=%s failed: %s", job_id, exc)
        raise self.retry(exc=exc)
