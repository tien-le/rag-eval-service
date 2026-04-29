"""Celery worker settings configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Celery worker configuration settings."""

    # Celery broker (Redis or RabbitMQ)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Worker concurrency
    CELERY_WORKER_CONCURRENCY: int = Field(default=4, ge=1, le=20)
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = Field(default=4, ge=1, le=10)

    # Task settings
    CELERY_TASK_ALWAYS_EAGER: bool = False  # Run tasks synchronously (for testing)
    CELERY_TASK_ACKS_LATE: bool = True  # Acknowledge after task completes
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True

    # Result expiration
    CELERY_RESULT_EXPIRES: int = 3600  # 1 hour
    CELERY_RESULT_EXTENDED: bool = True

    # Worker heartbeat
    CELERY_WORKER_HEARTBEAT_INTERVAL: int = 30

    # Queue configuration
    CELERY_DEFAULT_QUEUE: str = "default"
    CELERY_QUEUES: str = "default,workflow,evaluation,embedding,indexing,agent,llm,maintenance,dead_letter"

    # Scheduled tasks (beat schedule)
    CELERY_BEAT_SCHEDULE_ENABLED: bool = True
    CELERY_BEAT_MAX_LOOP_INTERVAL: int = 300  # 5 minutes

    # Redis specific
    CELERY_REDIS_MAX_CONNECTIONS: int = 50
    CELERY_REDIS_SOCKET_TIMEOUT: int = 30
    CELERY_REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # Task routing (JSON string)
    CELERY_TASK_ROUTES: str = "{}"

    # Dead letter queue
    CELERY_TASK_DLQ_ENABLED: bool = True
    CELERY_TASK_MAX_RETRIES: int = 3

    # Job status TTL in Redis (seconds)
    JOB_STATUS_TTL: int = 3600  # 1 hour

    class Config:
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_queues(self) -> list[str]:
        """Get list of configured queues."""
        return [q.strip() for q in self.CELERY_QUEUES.split(",") if q.strip()]

    def get_task_routes(self) -> dict[str, dict]:
        """Get task routing configuration."""
        import json

        try:
            routes = json.loads(self.CELERY_TASK_ROUTES)
            return {k: {"queue": v} for k, v in routes.items()}
        except json.JSONDecodeError:
            return {}
