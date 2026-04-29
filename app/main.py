"""FastAPI application factory and entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routers.admin_router import router as admin_router
from app.api.routers.auth_router import router as auth_router
from app.api.routers.eval_router import router as eval_router
from app.api.routers.health_router import router as health_router
from app.api.v1.eval_router import router as v1_eval_router
from app.api.v1.jobs_router import router as v1_jobs_router
from app.api.v2.eval_router import router as v2_eval_router
from app.api.v2.jobs_router import router as v2_jobs_router
from app.core.config.exceptions import register_exception_handlers
from app.core.config.logging import LoggingContextMiddleware, get_logger, setup_logging
from app.core.config.observability import (
    CorrelationTracingMiddleware,
    setup_observability,
)
from app.core.config.settings import Settings, get_settings
from app.core.middleware import (
    AuditMiddleware,
    AuthMiddleware,
    CorrelationIdMiddleware,
    ErrorMiddleware,
    LatencyTrackingMiddleware,
    RequestIdMiddleware,
    TenantMiddleware,
)

setup_logging()
setup_observability()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""

    settings: Settings = app.state.settings

    logger.info(
        "app.startup name=%s environment=%s",
        settings.APP_NAME,
        settings.ENVIRONMENT,
    )

    # --- Redis (used by v1 job store, rate limiter, Celery broker) ---
    from app.infra.cache.redis_client import close_redis_pool, init_redis_pool

    await init_redis_pool()
    logger.info("app.redis.ready")

    # --- Kafka publisher (v2 only; opt-in via KAFKA_ENABLED=true) ---
    if settings.KAFKA_ENABLED:
        from app.infra.event_bus.kafka import KafkaPublisher

        publisher = KafkaPublisher(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        await publisher.start()
        app.state.kafka_publisher = publisher
        logger.info("app.kafka.ready bootstrap=%s", settings.KAFKA_BOOTSTRAP_SERVERS)
    else:
        app.state.kafka_publisher = None
        logger.info(
            "app.kafka.disabled (set KAFKA_ENABLED=true to enable v2 endpoints)"
        )

    try:
        yield
    finally:
        logger.info("app.shutdown")

        await close_redis_pool()

        if settings.KAFKA_ENABLED and app.state.kafka_publisher:
            await app.state.kafka_publisher.stop()


def add_middlewares(app: FastAPI, settings: Settings) -> None:
    """Add middlewares.

    Middleware runs in reverse order (last added runs first).
    Order: Error -> Audit -> Latency -> RateLimit -> Tenant -> Auth -> Logging/CORS -> CorrelationId
    """
    # CORS must be early to handle preflight requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Correlation-ID",
            "X-Tenant-ID",
            "traceparent",
            "tracestate",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Correlation-ID",
            "X-Process-Time-Ms",
            "X-Tenant-ID",
            "traceparent",
        ],
        max_age=600,
    )

    # Logging & Tracing
    app.add_middleware(LoggingContextMiddleware)
    app.add_middleware(CorrelationTracingMiddleware)

    # Request/Response middleware (runs in reverse order of addition)
    # Error handling (outermost - catches all errors)
    app.add_middleware(ErrorMiddleware, include_details=not settings.is_production)

    # Audit logging for state-changing operations
    app.add_middleware(AuditMiddleware)

    # Latency tracking
    app.add_middleware(LatencyTrackingMiddleware, slow_threshold_ms=1000.0)

    # Rate limiting is handled by SlowAPI in app/core/security/rate_limiter.py
    # Use the limiter decorator on individual endpoints for granular control

    # Tenant resolution
    app.add_middleware(TenantMiddleware, default_tenant="default")

    # Auth extraction (runs early to set user context)
    app.add_middleware(AuthMiddleware)

    # Request ID generation (runs early)
    app.add_middleware(RequestIdMiddleware)

    # Correlation ID propagation (runs first - outermost)
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Correlation-ID",
    )


def include_routers(app: FastAPI, settings: Settings) -> None:
    api_prefix = getattr(settings, "API_PREFIX", "/api")

    # --- Legacy (no version prefix — backward compat) ---
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(eval_router, prefix=api_prefix)

    # --- Authentication (available on all versions) ---
    app.include_router(auth_router, prefix=api_prefix)

    # --- Admin (protected endpoints) ---
    app.include_router(admin_router, prefix=f"{api_prefix}")

    # --- v1: single service + Redis + Celery (1K RPM) ---
    app.include_router(v1_eval_router, prefix=f"{api_prefix}/v1")
    app.include_router(v1_jobs_router, prefix=f"{api_prefix}/v1")

    # --- v2: Kafka + worker pools (100K RPM) ---
    app.include_router(v2_eval_router, prefix=f"{api_prefix}/v2")
    app.include_router(v2_jobs_router, prefix=f"{api_prefix}/v2")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=getattr(settings, "APP_VERSION", getattr(settings, "VERSION", "1.0.0")),
        description=settings.DESCRIPTION,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings

    register_exception_handlers(app)
    add_middlewares(app, settings)
    include_routers(app, settings)
    FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
