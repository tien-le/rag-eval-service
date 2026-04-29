"""API routers for FastAPI."""

from app.api.routers.admin_router import router as admin_router
from app.api.routers.auth_router import router as auth_router
from app.api.routers.eval_router import router as eval_router
from app.api.routers.health_router import router as health_router

__all__ = [
    "admin_router",
    "auth_router",
    "eval_router",
    "health_router",
]
