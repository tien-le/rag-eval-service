"""Tracing setup: LangSmith + OpenTelemetry."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from asgi_correlation_id import correlation_id
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config.logging import get_logger
from app.core.config.settings import Settings, get_settings

logger = get_logger(__name__)


class CorrelationTracingMiddleware(BaseHTTPMiddleware):
    """Attach correlation_id to the active OpenTelemetry span."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            from opentelemetry import trace
            from opentelemetry.trace import INVALID_SPAN_CONTEXT
        except ImportError:
            return await call_next(request)

        corr_id = correlation_id.get()

        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx != INVALID_SPAN_CONTEXT and corr_id:
            span.set_attribute("correlation_id", corr_id)
            span.set_attribute("http.request_id", corr_id)

        return await call_next(request)


def setup_langsmith(settings: Settings) -> None:
    api_key = getattr(settings, "LANGSMITH_API_KEY", "")

    if not api_key:
        logger.info("langsmith.disabled")
        return

    if hasattr(api_key, "get_secret_value"):
        api_key = api_key.get_secret_value()

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
    os.environ.setdefault(
        "LANGCHAIN_PROJECT",
        getattr(settings, "LANGSMITH_PROJECT", settings.APP_NAME),
    )

    logger.info(
        "langsmith.enabled",
        project=os.environ.get("LANGCHAIN_PROJECT"),
    )


def setup_opentelemetry(settings: Settings) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except ImportError:
        logger.warning(
            "opentelemetry.dependencies_missing",
            detail=(
                "Install opentelemetry-api opentelemetry-sdk "
                "opentelemetry-exporter-otlp."
            ),
        )
        return

    current_provider = trace.get_tracer_provider()

    if isinstance(current_provider, TracerProvider):
        logger.info("opentelemetry.already_configured")
        return

    resource = Resource.create(
        {
            "service.name": settings.APP_NAME,
            "service.version": getattr(settings, "APP_VERSION", "unknown"),
            "deployment.environment": str(settings.ENVIRONMENT),
        }
    )

    provider = TracerProvider(resource=resource)

    endpoint = getattr(settings, "OTEL_EXPORTER_ENDPOINT", "").strip()
    console_enabled = getattr(settings, "OTEL_CONSOLE_EXPORTER_ENABLED", False)

    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
        except ImportError:
            logger.warning(
                "opentelemetry.otlp_exporter_missing",
                detail="Install opentelemetry-exporter-otlp.",
            )
        else:
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=endpoint),
                )
            )
            logger.info(
                "opentelemetry.otlp_exporter.enabled",
                endpoint=endpoint,
            )
    elif console_enabled:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("opentelemetry.console_exporter.enabled")
    else:
        logger.info("opentelemetry.exporter.disabled_local_tracing_enabled")
    trace.set_tracer_provider(provider)

    logger.info(
        "opentelemetry.enabled",
        service_name=settings.APP_NAME,
        environment=str(settings.ENVIRONMENT),
        exporter="otlp" if endpoint else "console",
    )


def setup_observability() -> None:
    settings = get_settings()

    setup_langsmith(settings)
    setup_opentelemetry(settings)

    logger.info(
        "observability.initialized",
        environment=str(settings.ENVIRONMENT),
    )
