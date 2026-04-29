"""v2 evaluation router — all evals are async, dispatched to Kafka (100K RPM).

POST /api/v2/eval/ragas/single-turn  → job_id  (non-blocking, Kafka publish)
POST /api/v2/eval/ragas/multi-turn   → job_id  (non-blocking, Kafka publish)

The API publishes an EvalRequestedEvent to the ``eval.requested`` Kafka topic
and returns immediately.  The standalone eval_worker pod picks it up, runs the
evaluation, writes the result to Redis (or Postgres in production), and emits
``eval.completed`` / ``eval.failed`` events.

Requires: KAFKA_ENABLED=true + KAFKA_BOOTSTRAP_SERVERS env vars.
Falls back to a 503 if Kafka is not configured.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.schemas.evaluation import (
    RagasMultiTurnRequest,
    RagasSingleTurnRequest,
)
from app.infra.event_bus.events import EvalRequestedEvent
from app.infra.event_bus.kafka import KafkaPublisher
from app.infra.jobs.redis_job_store import create_job
from app.schemas.job import AsyncJobResponse

router = APIRouter(prefix="/eval", tags=["v2 · Evaluation"])

TOPIC_EVAL_REQUESTED = "eval.requested"


def _get_kafka_publisher(request: Request) -> KafkaPublisher:
    publisher: KafkaPublisher | None = getattr(
        request.app.state, "kafka_publisher", None
    )
    if publisher is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Kafka is not enabled on this instance. "
                "Set KAFKA_ENABLED=true and KAFKA_BOOTSTRAP_SERVERS to use v2 endpoints."
            ),
        )
    return publisher


@router.post("/ragas/single-turn", response_model=AsyncJobResponse)
async def evaluate_single_turn_v2(
    payload: RagasSingleTurnRequest,
    publisher: KafkaPublisher = Depends(_get_kafka_publisher),
) -> AsyncJobResponse:
    job_id = await create_job("ragas_single_turn")
    event = EvalRequestedEvent(
        job_id=job_id,
        eval_type="single_turn",
        eval_input={
            "user_input": payload.user_input,
            "response": payload.response,
            "retrieved_contexts": payload.retrieved_contexts,
            "reference_contexts": payload.reference_contexts,
            "retrieved_context_ids": payload.retrieved_context_ids,
            "reference_context_ids": payload.reference_context_ids,
            "reference": payload.reference,
            "metric_names": payload.metric_names,
        },
    )
    await publisher.publish(TOPIC_EVAL_REQUESTED, asdict(event))
    return AsyncJobResponse(job_id=job_id)


@router.post("/ragas/multi-turn", response_model=AsyncJobResponse)
async def evaluate_multi_turn_v2(
    payload: RagasMultiTurnRequest,
    publisher: KafkaPublisher = Depends(_get_kafka_publisher),
) -> AsyncJobResponse:
    job_id = await create_job("ragas_multi_turn")
    event = EvalRequestedEvent(
        job_id=job_id,
        eval_type="multi_turn",
        eval_input={
            "messages": [m.model_dump() for m in payload.messages],
            "reference": payload.reference,
            "reference_topics": payload.reference_topics,
            "reference_tool_calls": (
                [tc.model_dump() for tc in payload.reference_tool_calls]
                if payload.reference_tool_calls is not None
                else None
            ),
            "metric_names": payload.metric_names,
        },
    )
    await publisher.publish(TOPIC_EVAL_REQUESTED, asdict(event))
    return AsyncJobResponse(job_id=job_id)
