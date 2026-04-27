
# if settings.SENTRY_DSN:
#     sentry_sdk.init(
#         dsn=settings.SENTRY_DSN,
#         # Add data like request headers and IP for users,
#         # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#         send_default_pii=True,
#     )

from app.core.logging_context import LoggingContextMiddleware
from fastapi import FastAPI

from asgi_correlation_id import CorrelationIdMiddleware

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