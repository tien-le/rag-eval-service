"""Authentication middleware for FastAPI."""

from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config.logging import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication and extract user context."""

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
        """Extract auth info and add to request state."""
        # Skip auth for exempt paths
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return await call_next(request)

        # Extract auth header if present
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Store raw auth header in state for downstream use
            request.state.authorization = auth_header

            # Try to extract user info from JWT (without full validation here)
            try:
                user_info = self._extract_user_from_token(auth_header)
                if user_info:
                    request.state.user_id = user_info.get("sub")
                    request.state.user_email = user_info.get("email")
                    request.state.user_permissions = user_info.get("permissions", [])
            except Exception as e:
                logger.debug("auth_extraction_failed path=%s error=%s", path, str(e))

        return await call_next(request)

    def _extract_user_from_token(self, auth_header: str) -> dict[str, Any] | None:
        """Extract user info from JWT without full validation.

        Full validation happens in the auth dependency.
        """
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]

        try:
            # Decode without verification to get payload for logging/context
            # Actual validation happens in the route dependencies
            import base64
            import json

            # Extract payload from JWT (middle segment)
            parts = token.split(".")
            if len(parts) != 3:
                return None

            # Add padding if needed
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return None
