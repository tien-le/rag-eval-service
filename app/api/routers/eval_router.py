"""Evaluation router for metric endpoints."""

from fastapi import APIRouter

from app.api.schemas.evaluation import (
    ClassificationMetricsRequest,
    ClassificationMetricsResponse,
    MetricCatalogResponse,
    RagasSingleTurnRequest,
    RagasSingleTurnResponse,
)
from app.infra.evaluation.ragas_adapter import RagasAdapter
from app.infra.llm_gateways.ollama_provider import (
    evaluator_embeddings,
    evaluator_model,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/eval", tags=["Evaluation"])


@router.get("/metrics", response_model=MetricCatalogResponse)
async def get_metric_catalog() -> MetricCatalogResponse:
    return MetricCatalogResponse(metrics=service.metric_catalog())


@router.post("/classification", response_model=ClassificationMetricsResponse)
async def evaluate_classification(
    payload: ClassificationMetricsRequest,
) -> ClassificationMetricsResponse:
    service = EvaluationService()
    result = service.evaluate_classification(
        actual=payload.actual,
        predicted=payload.predicted,
        positive_label=payload.positive_label,
    )
    return ClassificationMetricsResponse(**result)


@router.post("/ragas/single-turn", response_model=RagasSingleTurnResponse)
async def evaluate_ragas_single_turn(
    payload: RagasSingleTurnRequest,
) -> RagasSingleTurnResponse:
    service = EvaluationService(
        evaluator_llm=evaluator_model,
        evaluator_embeddings=evaluator_embeddings,
    )
    required_constructor_args = RagasAdapter.required_constructor_args(
        payload.metric_names
    )
    available_dependencies = service.evaluator_dependencies()
    evaluator_kwargs = {}
    if "llm" in required_constructor_args:
        evaluator_kwargs["llm"] = available_dependencies["llm"]
    if "embeddings" in required_constructor_args:
        evaluator_kwargs["embeddings"] = available_dependencies["embeddings"]

    result = await service.evaluate_ragas_single_turn(
        user_input=payload.user_input,
        response=payload.response,
        retrieved_contexts=payload.retrieved_contexts,
        reference_contexts=payload.reference_contexts,
        retrieved_context_ids=payload.retrieved_context_ids,
        reference_context_ids=payload.reference_context_ids,
        reference=payload.reference,
        metric_names=payload.metric_names,
        **evaluator_kwargs,
    )
    return RagasSingleTurnResponse(**result)
