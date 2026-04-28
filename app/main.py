"""FastAPI application factory and entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.health_router import router as health_router
from app.core.config.exceptions import register_exception_handlers
from app.core.config.logging import LoggingContextMiddleware, get_logger
from app.core.config.settings import Settings, get_settings

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

    try:
        # Initialize resources here:
        # app.state.container = get_container()
        # await init_database()
        # await init_redis()
        # setup_observability()

        yield

    finally:
        logger.info("app.shutdown")

        # Close resources here:
        # await close_redis()
        # await close_database()
        # await close_postgres_checkpoint_saver()


# def add_request_middleware(app: FastAPI) -> None:
#     @app.middleware("http")
#     async def request_context_middleware(
#         request: Request,
#         call_next: Callable[[Request], Awaitable[Response]],
#     ) -> Response:
#         request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
#         token = set_request_id(request_id)
#         started = perf_counter()

#         try:
#             response = await call_next(request)
#         except Exception:
#             elapsed_ms = (perf_counter() - started) * 1000
#             logger.exception(
#                 "api.request.failed method=%s path=%s request_id=%s elapsed_ms=%.1f",
#                 request.method,
#                 request.url.path,
#                 request_id,
#                 elapsed_ms,
#             )
#             raise
#         finally:
#             reset_request_id(token)

#         elapsed_ms = (perf_counter() - started) * 1000
#         response.headers["x-request-id"] = request_id
#         response.headers["x-process-time-ms"] = f"{elapsed_ms:.1f}"

#         logger.info(
#             "api.request method=%s path=%s status=%s request_id=%s elapsed_ms=%.1f",
#             request.method,
#             request.url.path,
#             response.status_code,
#             request_id,
#             elapsed_ms,
#         )
#         return response

# def add_cors_middleware(app: FastAPI, settings: Settings) -> None:
#     app.add_middleware(LoggingContextMiddleware)
#     app.add_middleware(
#         CorrelationIdMiddleware,
#         header_name="X-Request-ID",
#     )

#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=settings.CORS_ORIGINS,
#         allow_credentials=True,
#         allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
#         allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
#         expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
#         max_age=600,
#     )


def add_middlewares(app: FastAPI, settings: Settings) -> None:
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
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Correlation-ID",
            "X-Process-Time-Ms",
        ],
        max_age=600,
    )

    # Logging reads correlation_id.get()
    app.add_middleware(LoggingContextMiddleware)

    # Important: Starlette middleware runs in reverse order.
    # Add CorrelationIdMiddleware LAST so it runs FIRST.
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        update_request_header=True,
    )


def include_routers(app: FastAPI, settings: Settings) -> None:
    api_prefix = getattr(settings, "API_PREFIX", "/api")

    app.include_router(health_router, prefix=api_prefix)

    # app.include_router(auth_router, prefix=api_prefix)
    # app.include_router(user_router, prefix=api_prefix)
    # app.include_router(session_router, prefix=api_prefix)
    # app.include_router(chat_router, prefix=api_prefix)
    # app.include_router(human_approval_router, prefix=api_prefix)


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
    # add_request_middleware(app)
    # add_cors_middleware(app, settings)
    add_middlewares(app, settings)
    include_routers(app, settings)
    return app


app = create_app()
