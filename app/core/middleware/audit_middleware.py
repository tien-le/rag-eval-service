"""Audit logging middleware for FastAPI."""

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)

# Endpoints that should be audited
AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log audit events for state-changing operations."""

    def __init__(
        self,
        app,
        exempt_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Log audit events for state-changing operations."""
        path = request.url.path

        # Skip for exempt paths
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)

        should_audit = request.method in AUDIT_METHODS

        if should_audit:
            # Extract audit context before processing
            audit_record = self._create_audit_record(request)

        response = await call_next(request)

        if should_audit:
            # Complete audit record with response info
            audit_record["status_code"] = response.status_code
            self._log_audit(audit_record)

        return response

    def _create_audit_record(self, request: Request) -> dict[str, Any]:
        """Create audit record from request."""
        return {
            "timestamp": None,  # Set at logging time
            "method": request.method,
            "path": str(request.url),
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "request_id": getattr(request.state, "request_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
            "tenant_id": getattr(request.state, "tenant_id", None),
            "user_id": getattr(request.state, "user_id", None),
        }

    def _log_audit(self, record: dict[str, Any]) -> None:
        """Log audit record."""
        from datetime import UTC, datetime

        record["timestamp"] = datetime.now(UTC).isoformat()

        logger.info(
            "audit_event action=%s path=%s user=%s tenant=%s",
            record.get("method"),
            record.get("path"),
            record.get("user_id"),
            record.get("tenant_id"),
            extra={"audit": record},
        )
