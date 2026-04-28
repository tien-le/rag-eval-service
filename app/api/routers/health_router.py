"""Health Router"""

from fastapi import APIRouter

from app.core.config.settings import get_settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Check API health",
    description=(
        "Use this endpoint first to verify the API is reachable "
        "before testing authenticated flows."
    ),
)
async def health_check() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG_MODE,
    }
