"""Correlation ID middleware for distributed tracing."""

from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)
CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to propagate correlation IDs across service boundaries."""

    def __init__(self, app, header_name: str = CORRELATION_ID_HEADER):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Propagate correlation ID or generate new one."""
        # Get correlation ID from incoming request or generate new
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid4())

        # Store in request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response
        response.headers[self.header_name] = correlation_id

        return response


def get_correlation_id(request: Request) -> str | None:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", None)
