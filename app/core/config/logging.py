import logging
import logging.config
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import structlog
from asgi_correlation_id import correlation_id
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config.settings import get_settings
from app.core.security import redact_sensitive_data

logger = structlog.get_logger(__name__)


class LoggingContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()

        request_id = correlation_id.get()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=request_id,
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

        if request_id:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = request_id

        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        structlog.contextvars.clear_contextvars()
        return response


def setup_logging() -> None:
    settings = get_settings()

    log_level = settings.LOG_LEVEL.upper()
    is_local = settings.is_development or settings.is_testing

    log_dir = Path("var/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_sensitive_data,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if is_local
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "structlog",
            "level": log_level,
        }
    }

    root_handlers = ["console"]

    if settings.is_production:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_dir / "app.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "structlog",
            "level": log_level,
        }
        root_handlers.append("file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structlog": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": renderer,
                    "foreign_pre_chain": shared_processors,
                },
            },
            "handlers": handlers,
            "loggers": {
                "": {
                    "handlers": root_handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "app": {
                    "handlers": root_handlers,
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "httpx": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "httpcore": {
                    "handlers": root_handlers,
                    "level": "WARNING",
                    "propagate": False,
                },
                "langchain": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
                "ragas": {
                    "handlers": root_handlers,
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
