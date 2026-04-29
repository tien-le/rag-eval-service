"""v2 standalone Kafka consumer worker (100K RPM).

Run as a separate process / Kubernetes pod:

    python -m app.workers.eval_worker

Each pod is a member of the consumer group ``eval-workers``.
Kafka assigns partitions across pods automatically, giving horizontal scale.

Scaling guide:
  - Partitions on topic ``eval.requested`` ≥ number of pods for best parallelism.
  - Each pod runs ONE evaluation at a time (CPU-bound Ragas metric evaluation).
  - Add pods to increase throughput; Kafka rebalances partitions automatically.

v2 job status is written to Redis (same store as v1) and to Kafka topics
``eval.completed`` / ``eval.failed`` for downstream consumers.

TODO (production v2): replace redis_job_store with a Postgres-backed store
using the async_jobs table so results are durable beyond the Redis TTL.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from app.core.config.settings import get_settings
from app.infra.event_bus.events import EvalCompletedEvent, EvalFailedEvent
from app.infra.event_bus.kafka import KafkaPublisher
from app.infra.jobs.redis_job_store import create_job, update_job

logger = logging.getLogger(__name__)

TOPIC_EVAL_REQUESTED = "eval.requested"
TOPIC_EVAL_COMPLETED = "eval.completed"
TOPIC_EVAL_FAILED = "eval.failed"
GROUP_ID = "eval-workers"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _handle(event: dict, publisher: KafkaPublisher) -> None:
    job_id: str = event["job_id"]
    eval_type: str = event["eval_type"]
    eval_input: dict = event["eval_input"]

    # Import heavy deps inside handler to allow fast worker boot
    from app.infra.llm_gateways.ollama_provider import (
        evaluator_embeddings,
        evaluator_model,
    )
    from app.services.evaluation_service import EvaluationService

    svc = EvaluationService(
        evaluator_llm=evaluator_model,
        evaluator_embeddings=evaluator_embeddings,
    )

    await update_job(job_id, status="running", started_at=_now())

    try:
        if eval_type == "single_turn":
            result = await svc.evaluate_ragas_single_turn(**eval_input)
        elif eval_type == "multi_turn":
            result = await svc.evaluate_ragas_multi_turn(**eval_input)
        else:
            raise ValueError(f"Unknown eval_type: {eval_type!r}")

        await update_job(job_id, status="completed", result=result, completed_at=_now())
        await publisher.publish(
            TOPIC_EVAL_COMPLETED,
            asdict(EvalCompletedEvent(job_id=job_id, result=result)),
        )
        logger.info("eval_worker.completed job_id=%s eval_type=%s", job_id, eval_type)

    except Exception as exc:
        error = str(exc)
        logger.exception("eval_worker.failed job_id=%s error=%s", job_id, error)
        await update_job(job_id, status="failed", error=error, completed_at=_now())
        await publisher.publish(
            TOPIC_EVAL_FAILED,
            asdict(EvalFailedEvent(job_id=job_id, error=error)),
        )


async def main() -> None:
    try:
        from aiokafka import AIOKafkaConsumer
    except ImportError as exc:
        raise SystemExit(
            "aiokafka is required for v2 eval_worker. "
            "Add aiokafka to requirements.txt and reinstall."
        ) from exc

    s = get_settings()
    publisher = KafkaPublisher(bootstrap_servers=s.KAFKA_BOOTSTRAP_SERVERS)
    await publisher.start()

    consumer = AIOKafkaConsumer(
        TOPIC_EVAL_REQUESTED,
        bootstrap_servers=s.KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        value_deserializer=lambda m: json.loads(m.decode()),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info(
        "eval_worker.listening topic=%s group=%s", TOPIC_EVAL_REQUESTED, GROUP_ID
    )

    try:
        async for msg in consumer:
            await _handle(msg.value, publisher)
    finally:
        await consumer.stop()
        await publisher.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
