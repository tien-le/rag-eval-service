"""Tenant middleware for multi-tenant request handling."""

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)
TENANT_HEADER = "X-Tenant-ID"


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and validate tenant context."""

    def __init__(
        self,
        app,
        exempt_paths: list[str] | None = None,
        default_tenant: str = "default",
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self.default_tenant = default_tenant

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Extract tenant ID and add to request state."""
        path = request.url.path

        # Skip for exempt paths
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)

        # Extract tenant ID from header
        tenant_id = request.headers.get(TENANT_HEADER)

        # Fall back to tenant from JWT if available
        if not tenant_id:
            tenant_id = getattr(request.state, "tenant_id_from_jwt", None)

        # Fall back to default
        if not tenant_id:
            tenant_id = self.default_tenant

        # Store in request state
        request.state.tenant_id = tenant_id
        request.state.tenant_header = tenant_id  # For response headers

        # Log tenant context for observability
        logger.debug(
            "tenant_context tenant_id=%s path=%s method=%s",
            tenant_id,
            path,
            request.method,
        )

        response = await call_next(request)

        # Add tenant info to response headers
        response.headers["X-Tenant-ID"] = tenant_id

        return response
