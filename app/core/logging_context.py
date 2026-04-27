import time
from collections.abc import Awaitable, Callable

import structlog
from asgi_correlation_id import correlation_id
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class LoggingContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id.get(),
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.exception(
                "request_failed",
                duration_ms=duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
    