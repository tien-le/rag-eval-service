"""Evaluation router for metric endpoints."""

from fastapi import APIRouter, Depends

from app.api.schemas.evaluation import (
    ClassificationMetricsRequest,
    ClassificationMetricsResponse,
    MetricCatalogResponse,
    RagasMultiTurnRequest,
    RagasMultiTurnResponse,
    RagasSingleTurnRequest,
    RagasSingleTurnResponse,
)
from app.infra.llm_gateways.ollama_provider import (
    evaluator_embeddings,
    evaluator_model,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/eval", tags=["Evaluation"])


def _get_evaluation_service() -> EvaluationService:
    """Dependency injection for EvaluationService."""
    return EvaluationService(
        evaluator_llm=evaluator_model,
        evaluator_embeddings=evaluator_embeddings,
    )


@router.get("/metrics", response_model=MetricCatalogResponse)
async def get_metric_catalog(
    service: EvaluationService = Depends(_get_evaluation_service),
) -> MetricCatalogResponse:
    return MetricCatalogResponse(metrics=service.metric_catalog())


@router.post("/classification", response_model=ClassificationMetricsResponse)
async def evaluate_classification(
    payload: ClassificationMetricsRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> ClassificationMetricsResponse:
    result = service.evaluate_classification(
        actual=payload.actual,
        predicted=payload.predicted,
        positive_label=payload.positive_label,
    )
    return ClassificationMetricsResponse(**result)


@router.post("/ragas/single-turn", response_model=RagasSingleTurnResponse)
async def evaluate_ragas_single_turn(
    payload: RagasSingleTurnRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> RagasSingleTurnResponse:
    result = await service.evaluate_ragas_single_turn(
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
async def evaluate_ragas_multi_turn(
    payload: RagasMultiTurnRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> RagasMultiTurnResponse:
    result = await service.evaluate_ragas_multi_turn(
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
