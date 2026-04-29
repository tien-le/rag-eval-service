"""Error handling middleware for FastAPI."""

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.config.logging import get_logger

logger = get_logger(__name__)


class ErrorMiddleware(BaseHTTPMiddleware):
    """Middleware to catch and handle unhandled exceptions."""

    def __init__(
        self,
        app,
        include_details: bool = False,
    ):
        super().__init__(app)
        self.include_details = include_details

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Catch and handle exceptions."""
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.exception(
                "unhandled_error path=%s method=%s request_id=%s error=%s",
                request.url.path,
                request.method,
                request_id,
                str(exc),
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(exc).__name__,
                },
            )

            # Return generic error response
            detail = str(exc) if self.include_details else "Internal server error"

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "internal_error",
                        "message": detail,
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id},
            )
