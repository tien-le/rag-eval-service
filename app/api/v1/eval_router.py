"""v1 evaluation router — sync endpoints and Celery-backed async variants.

Sync  : POST /api/v1/eval/ragas/single-turn        → wait for result
Async : POST /api/v1/eval/ragas/single-turn/async  → job_id (poll /v1/jobs/{id})

The async endpoints dispatch a Celery task to the ``evaluation`` queue
(broker: Redis) and return immediately with the job_id.
Workers update job status in Redis via redis_job_store.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps.rate_limit import (
    rate_limit_classification,
    rate_limit_metrics_catalog,
    rate_limit_ragas_async,
    rate_limit_ragas_expensive,
)
from app.api.schemas.evaluation import (
    ClassificationMetricsRequest,
    ClassificationMetricsResponse,
    MetricCatalogResponse,
    RagasMultiTurnRequest,
    RagasMultiTurnResponse,
    RagasSingleTurnRequest,
    RagasSingleTurnResponse,
)
from app.infra.jobs.redis_job_store import create_job
from app.infra.llm_gateways.ollama_provider import evaluator_embeddings, evaluator_model
from app.schemas.job import AsyncJobResponse
from app.services.evaluation_service import EvaluationService
from app.workers.tasks.eval_tasks import ragas_multi_turn_task, ragas_single_turn_task

router = APIRouter(prefix="/eval", tags=["v1 · Evaluation"])


def _get_service() -> EvaluationService:
    return EvaluationService(
        evaluator_llm=evaluator_model,
        evaluator_embeddings=evaluator_embeddings,
    )


# ---------------------------------------------------------------------------
# Sync endpoints (same semantics as /api/eval/*, added here for versioned path)
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=MetricCatalogResponse)
async def get_metric_catalog(
    rate_limit: Annotated[dict, rate_limit_metrics_catalog],
    svc: EvaluationService = Depends(_get_service),
) -> MetricCatalogResponse:
    return MetricCatalogResponse(metrics=svc.metric_catalog())


@router.post("/classification", response_model=ClassificationMetricsResponse)
async def evaluate_classification(
    payload: ClassificationMetricsRequest,
    rate_limit: Annotated[dict, rate_limit_classification],
    svc: EvaluationService = Depends(_get_service),
) -> ClassificationMetricsResponse:
    result = svc.evaluate_classification(
        actual=payload.actual,
        predicted=payload.predicted,
        positive_label=payload.positive_label,
    )
    return ClassificationMetricsResponse(**result)


@router.post("/ragas/single-turn", response_model=RagasSingleTurnResponse)
async def evaluate_single_turn(
    payload: RagasSingleTurnRequest,
    rate_limit: Annotated[dict, rate_limit_ragas_expensive],
    svc: EvaluationService = Depends(_get_service),
) -> RagasSingleTurnResponse:
    result = await svc.evaluate_ragas_single_turn(
        user_input=payload.user_input,
        response=payload.response,
        retrieved_contexts=payload.retrieved_contexts,
        reference_contexts=payload.reference_contexts,
        retrieved_context_ids=payload.retrieved_context_ids,
        reference_context_ids=payload.reference_context_ids,
        reference=payload.reference,
        metric_names=payload.metric_names,
    )
    return RagasSingleTurnResponse(**result)


@router.post("/ragas/multi-turn", response_model=RagasMultiTurnResponse)
async def evaluate_multi_turn(
    payload: RagasMultiTurnRequest,
    rate_limit: Annotated[dict, rate_limit_ragas_expensive],
    svc: EvaluationService = Depends(_get_service),
) -> RagasMultiTurnResponse:
    result = await svc.evaluate_ragas_multi_turn(
        messages=[m.model_dump() for m in payload.messages],
        reference=payload.reference,
        reference_topics=payload.reference_topics,
        reference_tool_calls=(
            [tc.model_dump() for tc in payload.reference_tool_calls]
            if payload.reference_tool_calls is not None
            else None
        ),
        metric_names=payload.metric_names,
    )
    return RagasMultiTurnResponse(**result)


# ---------------------------------------------------------------------------
# Async endpoints — dispatch Celery task, return job_id immediately
# ---------------------------------------------------------------------------


@router.post("/ragas/single-turn/async", response_model=AsyncJobResponse)
async def evaluate_single_turn_async(
    rate_limit: Annotated[dict, rate_limit_ragas_async],
    payload: RagasSingleTurnRequest,
) -> AsyncJobResponse:
    job_id = await create_job("ragas_single_turn")
    ragas_single_turn_task.delay(
        job_id,
        {
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
    return AsyncJobResponse(job_id=job_id)


@router.post("/ragas/multi-turn/async", response_model=AsyncJobResponse)
async def evaluate_multi_turn_async(
    rate_limit: Annotated[dict, rate_limit_ragas_async],
    payload: RagasMultiTurnRequest,
) -> AsyncJobResponse:
    job_id = await create_job("ragas_multi_turn")
    ragas_multi_turn_task.delay(
        job_id,
        {
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
    return AsyncJobResponse(job_id=job_id)
