"""Rate limit middleware for FastAPI."""

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for global rate limiting."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 1000,
        exempt_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.exempt_paths = exempt_paths or ["/health"]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Apply rate limiting to requests."""
        path = request.url.path

        # Skip for exempt paths
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)

        # TODO: Implement distributed rate limiting with Redis
        # For now, pass through

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = "999"  # Placeholder
        response.headers["X-RateLimit-Window"] = "60"

        return response
