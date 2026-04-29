"""Request ID middleware for FastAPI."""

from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate request IDs."""

    def __init__(self, app, header_name: str = REQUEST_ID_HEADER):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Generate request ID if not present and add to response."""
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid4())

        # Store in request state for access in routes
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", str(uuid4()))
