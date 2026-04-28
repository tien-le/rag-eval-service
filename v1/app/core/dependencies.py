from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.user import UserService


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    return UserService(session)


from functools import lru_cache

from app.application.evaluation.service import EvaluationService
from app.infra.ragas.provider import RagasRetrievalQualityEvaluator


@lru_cache
def get_evaluation_service() -> EvaluationService:
    return EvaluationService(evaluator=RagasRetrievalQualityEvaluator())
