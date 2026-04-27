from fastapi import APIRouter, Depends, Header
from schemas.evaluation import EvaluationRequest, EvaluationCreatedResponse
from services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


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
