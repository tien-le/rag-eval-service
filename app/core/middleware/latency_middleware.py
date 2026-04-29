"""Latency tracking middleware for FastAPI."""

import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)
LATENCY_HEADER = "X-Process-Time-Ms"


class LatencyTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track and log request latency."""

    def __init__(
        self,
        app,
        slow_threshold_ms: float = 1000.0,
        log_all_requests: bool = False,
    ):
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
        self.log_all_requests = log_all_requests

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Track request processing time."""
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            # Calculate latency
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            # Add latency header to response
            # Note: response might not exist if exception occurred
            try:
                response.headers[LATENCY_HEADER] = f"{latency_ms:.2f}"
            except NameError:
                pass  # response doesn't exist due to exception

            # Log slow requests or all requests if configured
            if latency_ms > self.slow_threshold_ms or self.log_all_requests:
                log_level = "warning" if latency_ms > self.slow_threshold_ms else "info"
                getattr(logger, log_level)(
                    "request_latency path=%s method=%s latency_ms=%.2f",
                    request.url.path,
                    request.method,
                    latency_ms,
                    extra={
                        "latency_ms": latency_ms,
                        "path": request.url.path,
                        "method": request.method,
                    },
                )

        return response
