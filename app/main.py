from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging_context import LoggingContextMiddleware
from app.db.qdrant_provider import qdrant_client
from app.core.logging import setup_logging, get_logger

# from app.db.mongodb_provider import mongodb_client
from app.db.sqlite_provider import sqlite_provider
from app.db.postgresql_provider import postgresql_provider
from fastapi import FastAPI

from asgi_correlation_id import CorrelationIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles:
    - Database connection initialization (startup)
    - Database connection cleanup (shutdown)
    - Optional MongoDB and Qdrant connections
    """
    # Startup: Initialize logging and database connections
    setup_logging()
    logger = get_logger(__name__)

    logger.info(
        "Initializing database connections",
        environment=settings.ENVIRONMENT.value,
        db_provider=settings.DB_PROVIDER.value,
    )

    # Initialize database based on DB_PROVIDER setting
    if settings.DB_PROVIDER.value == "sqlite":
        await sqlite_provider.connect()
        logger.info("SQLite database initialized")
    elif settings.DB_PROVIDER.value in ("supabase", "postgresql"):
        await postgresql_provider.connect()
        provider_name = (
            "Supabase" if settings.DB_PROVIDER.value == "supabase" else "PostgreSQL"
        )
        logger.info(f"{provider_name} database initialized")
    else:
        raise ValueError(
            f"Unsupported DB_PROVIDER: {settings.DB_PROVIDER.value}. "
            "Supported values: supabase, postgresql, sqlite"
        )

    # Initialize MongoDB if configured
    # if settings.MONGODB_URL:
    #     try:
    #         await mongodb_client.connect()
    #         logger.info(
    #             "MongoDB connected", extra={"database": settings.MONGODB_DATABASE}
    #         )
    #     except Exception as e:
    #         logger.warning("Failed to connect to MongoDB", extra={"error": str(e)})

    # Initialize Qdrant if configured
    if settings.QDRANT_URL:
        try:
            await qdrant_client.connect()
            logger.info("Qdrant connected", extra={"url": settings.QDRANT_URL})
        except Exception as e:
            logger.warning("Failed to connect to Qdrant", extra={"error": str(e)})

    logger.info("Application startup complete")

    yield

    # Shutdown: Close database connections
    logger.info("Shutting down database connections")

    # Close database based on DB_PROVIDER setting
    if settings.DB_PROVIDER.value == "sqlite":
        await sqlite_provider.disconnect()
        logger.info("SQLite database closed")
    elif settings.DB_PROVIDER.value in ("supabase", "postgresql"):
        await postgresql_provider.disconnect()
        provider_name = (
            "Supabase" if settings.DB_PROVIDER.value == "supabase" else "PostgreSQL"
        )
        logger.info(f"{provider_name} database closed")

    # Close MongoDB if connected
    # if mongodb_client.client is not None:
    #     await mongodb_client.disconnect()
    #     logger.info("MongoDB disconnected")

    # Close Qdrant if connected
    if qdrant_client.client is not None:
        await qdrant_client.disconnect()
        logger.info("Qdrant disconnected")

    logger.info("Application shutdown complete")


# if settings.SENTRY_DSN:
#     sentry_sdk.init(
#         dsn=settings.SENTRY_DSN,
#         # Add data like request headers and IP for users,
#         # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#         send_default_pii=True,
#     )

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add correlation ID middleware first (before other middleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(LoggingContextMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Status dictionary
    """
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT.value,
        "version": settings.VERSION,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}!",
        "version": settings.VERSION,
        "docs": "/docs" if not settings.is_production else "disabled",
    }
