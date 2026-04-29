"""Authentication dependencies for FastAPI."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config.logging import get_logger
from app.core.security.jwt_service import JWTService, get_jwt_service

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Authenticated user context."""

    def __init__(
        self,
        user_id: str | None = None,
        email: str | None = None,
        permissions: list[str] | None = None,
        token_payload: dict[str, Any] | None = None,
    ):
        self.user_id = user_id
        self.email = email
        self.permissions = permissions or []
        self.token_payload = token_payload or {}

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.

        Supports wildcard patterns (e.g., 'admin:*' matches 'admin:read').
        """
        for user_perm in self.permissions:
            if user_perm == permission:
                return True
            # Handle wildcard patterns like "admin:*"
            if user_perm.endswith(":*"):
                prefix = user_perm[:-2]
                if permission.startswith(prefix + ":"):
                    return True
        return False

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> CurrentUser:
    """Extract and validate current user from JWT token.

    Args:
        credentials: HTTP Authorization header credentials
        jwt_service: JWT validation service

    Returns:
        CurrentUser context

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = await jwt_service.validate_token(token)
    except Exception as e:
        logger.warning("token_validation_failed error=%s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    return CurrentUser(
        user_id=payload.get("sub"),
        email=payload.get("email"),
        permissions=payload.get("permissions", []),
        token_payload=payload,
    )


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> CurrentUser | None:
    """Extract user from JWT token if present, otherwise return None."""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, jwt_service)
    except HTTPException:
        return None


class PermissionChecker:
    """Dependency for checking user permissions."""

    def __init__(self, required_permissions: list[str], require_all: bool = True):
        self.required_permissions = required_permissions
        self.require_all = require_all

    async def __call__(
        self, user: Annotated[CurrentUser, Depends(get_current_user)]
    ) -> CurrentUser:
        """Check permissions and return user if authorized."""
        if self.require_all:
            has_permissions = all(
                user.has_permission(p) for p in self.required_permissions
            )
        else:
            has_permissions = any(
                user.has_permission(p) for p in self.required_permissions
            )

        if not has_permissions:
            logger.warning(
                "permission_denied user=%s required=%s has=%s",
                user.user_id,
                self.required_permissions,
                user.permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user


def require_permissions(
    *permissions: str,
    require_all: bool = True,
):
    """Create a dependency that requires specific permissions.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[CurrentUser, Depends(require_permissions("admin:read"))]
        ):
            ...
    """
    return Depends(PermissionChecker(list(permissions), require_all))


# Common permission requirements
RequireAdmin = require_permissions("admin:*", require_all=False)
RequireRead = require_permissions("eval:read", "workflow:read", require_all=False)
RequireWrite = require_permissions("eval:write", "workflow:write", require_all=False)
