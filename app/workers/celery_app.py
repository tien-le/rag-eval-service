"""Celery application for v1 async job processing (1K RPM, Redis broker)."""

from celery import Celery

from app.core.config.settings import get_settings

_s = get_settings()

celery_app = Celery(
    "rag_eval",
    broker=_s.CELERY_BROKER_URL,
    backend=_s.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks.eval_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Reliability: only ack after the task fully completes
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Routing: each domain has its own queue so workers can be scaled independently
    task_routes={
        "eval.*": {"queue": "evaluation"},
        "embedding.*": {"queue": "embedding"},
        "maintenance.*": {"queue": "maintenance"},
    },
    task_default_queue="evaluation",
    # Dead-letter: failed tasks land in dead_letter queue after max_retries
    task_queues={
        "evaluation": {},
        "embedding": {},
        "maintenance": {},
        "dead_letter": {},
    },
    # Result expiry: keep results for 1 hour (matches redis_job_store TTL)
    result_expires=3600,
)
