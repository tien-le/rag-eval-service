from fastapi import APIRouter, Depends, Header

from app.schemas.evaluation import EvaluationCreatedResponse, EvaluationRequest
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post("", response_model=EvaluationCreatedResponse)
async def create_evaluation(
    payload: EvaluationRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: EvaluationService = Depends(),
):
    return await service.create_evaluation(
        payload=payload,
        idempotency_key=idempotency_key,
    )


from fastapi import APIRouter, Depends

from app.application.evaluation.service import EvaluationService
from app.core.dependencies import get_evaluation_service
from app.schemas.evaluation import RetrievalQualityRequest, RetrievalQualityResponse


@router.post(
    "/retrieval-quality",
    response_model=RetrievalQualityResponse,
)
async def evaluate_retrieval_quality(
    request: RetrievalQualityRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> RetrievalQualityResponse:
    scores = await service.evaluate_retrieval_quality(
        question=request.question,
        contexts=request.contexts,
        reference_answer=request.reference_answer,
        metrics=[metric.value for metric in request.metrics],
    )

    return RetrievalQualityResponse(
        scores=scores,
        details={
            "provider": "ragas",
            "metrics": [metric.value for metric in request.metrics],
        },
    )
