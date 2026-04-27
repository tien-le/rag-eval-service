# services/evaluation_service.py

from uuid import uuid4
from app.core.enums import RunStatus
from app.schemas.evaluation import EvaluationRequest
from app.services.cost_service import CostService
from app.services.idempotency_service import IdempotencyService
from app.services.ragas_service import RagasService


class EvaluationService:
    def __init__(self):
        self.cost_service = CostService()
        self.idempotency_service = IdempotencyService()
        self.ragas_service = RagasService()

    async def create_evaluation(
        self,
        payload: EvaluationRequest,
        idempotency_key: str,
    ):
        cached_response = await self.idempotency_service.get_existing_response(
            idempotency_key=idempotency_key,
            payload=payload,
        )

        if cached_response:
            return cached_response

        total_items = len(payload.items or [])

        estimated_cost = self.cost_service.estimate(
            item_count=total_items,
            metrics=payload.metrics,
            judge_model=payload.judge_model,
        )

        run_id = f"run_{uuid4().hex}"

        # Persist run here in real implementation.
        # await run_repository.create(...)

        if total_items == 1:
            result = await self.ragas_service.evaluate_single(
                run_id=run_id,
                item=payload.items[0],
                metrics=payload.metrics,
                judge_model=payload.judge_model,
            )

            response = {
                "run_id": run_id,
                "status": RunStatus.COMPLETED,
                "total_items": 1,
                "estimated_cost_usd": estimated_cost,
                "result": result,
            }

        else:
            # Queue async job in real implementation.
            response = {
                "run_id": run_id,
                "status": RunStatus.QUEUED,
                "total_items": total_items,
                "estimated_cost_usd": estimated_cost,
            }

        await self.idempotency_service.save_response(
            idempotency_key=idempotency_key,
            payload=payload,
            response=response,
        )

        return response
