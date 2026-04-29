"""Admin router for system administration endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser, get_current_user, require_permissions
from app.api.deps.rate_limit import (
    rate_limit_admin_read,
    rate_limit_admin_write,
)
from app.api.deps.tenant import get_tenant_id
from app.core.config.logging import get_logger
from app.core.config.settings import Settings, get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    """Create user request."""

    username: str = Field(
        ..., min_length=1, max_length=100, description="Unique username"
    )
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    is_active: bool = Field(default=True, description="Whether user is active")


class UserResponse(BaseModel):
    """User response model."""

    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: str | None = Field(None, description="Creation timestamp")


class UserListResponse(BaseModel):
    """User list response."""

    users: list[UserResponse] = Field(default_factory=list, description="List of users")
    total: int = Field(..., description="Total number of users")


class UpdateUserRequest(BaseModel):
    """Update user request."""

    email: str | None = Field(None, description="New email")
    password: str | None = Field(None, min_length=8, description="New password")
    permissions: list[str] | None = Field(None, description="New permissions")
    is_active: bool | None = Field(None, description="Active status")


class SystemStatusResponse(BaseModel):
    """System status response."""

    status: str = Field(..., description="System status")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    timestamp: str = Field(..., description="Current timestamp")


class AuditLogEntry(BaseModel):
    """Audit log entry."""

    timestamp: str = Field(..., description="Event timestamp")
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path")
    user_id: str | None = Field(None, description="User ID")
    tenant_id: str | None = Field(None, description="Tenant ID")
    status_code: int | None = Field(None, description="Response status code")
    client_ip: str | None = Field(None, description="Client IP address")


# In-memory user store (replace with database in production)
_users: dict[str, dict[str, Any]] = {}


def _hash_password(password: str) -> str:
    """Hash a password (simple implementation - use bcrypt in production)."""
    import hashlib

    salt = "dev-salt-change-in-production"  # In production, use random salt per user
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return _hash_password(password) == hashed


def _get_users_store() -> dict[str, dict[str, Any]]:
    """Get the users store (in production, this would be a database)."""
    return _users


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user with specified permissions.",
    dependencies=[require_permissions("admin:write")],
)
async def create_user(
    request: CreateUserRequest,
    rate_limit: Annotated[dict, rate_limit_admin_write],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    """Create a new user in the system."""
    users = _get_users_store()

    # Check if username exists
    for user in users.values():
        if user["username"] == request.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with username '{request.username}' already exists",
            )

    # Create user
    user_id = str(uuid4())
    from datetime import UTC, datetime

    created_at = datetime.now(UTC).isoformat()

    user_data = {
        "user_id": user_id,
        "username": request.username,
        "email": request.email,
        "password_hash": _hash_password(request.password),
        "permissions": request.permissions or ["eval:read", "workflow:read"],
        "is_active": request.is_active,
        "tenant_id": tenant_id,
        "created_at": created_at,
    }

    users[user_id] = user_data

    logger.info(
        "user_created user_id=%s username=%s tenant=%s by_admin",
        user_id,
        request.username,
        tenant_id,
    )

    return UserResponse(
        user_id=user_id,
        username=request.username,
        email=request.email,
        permissions=user_data["permissions"],
        is_active=request.is_active,
        created_at=created_at,
    )


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    description="Get a list of all users in the system.",
    dependencies=[require_permissions("admin:read")],
)
async def list_users(
    rate_limit: Annotated[dict, rate_limit_admin_read],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserListResponse:
    """List all users in the system."""
    users = _get_users_store()

    # Filter by tenant if needed, or show all for admin
    user_list = [
        UserResponse(
            user_id=u["user_id"],
            username=u["username"],
            email=u["email"],
            permissions=u.get("permissions", []),
            is_active=u.get("is_active", True),
            created_at=u.get("created_at"),
        )
        for u in users.values()
    ]

    return UserListResponse(users=user_list, total=len(user_list))


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get details of a specific user.",
    dependencies=[require_permissions("admin:read")],
)
async def get_user(
    user_id: str,
    rate_limit: Annotated[dict, rate_limit_admin_read],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    """Get a specific user by ID."""
    users = _get_users_store()

    user = users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        permissions=user.get("permissions", []),
        is_active=user.get("is_active", True),
        created_at=user.get("created_at"),
    )


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user details.",
    dependencies=[require_permissions("admin:write")],
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    rate_limit: Annotated[dict, rate_limit_admin_write],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> UserResponse:
    """Update a user's details."""
    users = _get_users_store()

    user = users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    # Update fields if provided
    if request.email is not None:
        user["email"] = request.email
    if request.password is not None:
        user["password_hash"] = _hash_password(request.password)
    if request.permissions is not None:
        user["permissions"] = request.permissions
    if request.is_active is not None:
        user["is_active"] = request.is_active

    logger.info("user_updated user_id=%s tenant=%s", user_id, tenant_id)

    return UserResponse(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        permissions=user.get("permissions", []),
        is_active=user.get("is_active", True),
        created_at=user.get("created_at"),
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user from the system.",
    dependencies=[require_permissions("admin:write")],
)
async def delete_user(
    user_id: str,
    rate_limit: Annotated[dict, rate_limit_admin_write],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> None:
    """Delete a user from the system."""
    users = _get_users_store()

    if user_id not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    del users[user_id]

    logger.info("user_deleted user_id=%s tenant=%s", user_id, tenant_id)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=dict[str, str],
    summary="Reset user password",
    description="Generate a temporary password for a user.",
    dependencies=[require_permissions("admin:write")],
)
async def reset_user_password(
    user_id: str,
    rate_limit: Annotated[dict, rate_limit_admin_write],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> dict[str, str]:
    """Reset a user's password and return a temporary password."""
    users = _get_users_store()

    user = users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    # Generate temporary password
    import secrets

    temp_password = secrets.token_urlsafe(12)
    user["password_hash"] = _hash_password(temp_password)
    user["requires_password_change"] = True

    logger.info("user_password_reset user_id=%s tenant=%s", user_id, tenant_id)

    return {
        "message": "Password has been reset. User must change password on next login.",
        "temporary_password": temp_password,
    }


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    summary="Get system status",
    description="Get current system status and health information.",
    dependencies=[require_permissions("admin:read")],
)
async def get_system_status(
    rate_limit: Annotated[dict, rate_limit_admin_read],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SystemStatusResponse:
    """Get system status information."""
    from datetime import UTC, datetime

    return SystemStatusResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post(
    "/system/maintenance",
    response_model=dict[str, str],
    summary="Trigger maintenance task",
    description="Trigger a system maintenance task.",
    dependencies=[require_permissions("admin:write")],
)
async def trigger_maintenance(
    task: str,
    rate_limit: Annotated[dict, rate_limit_admin_write],
    user: Annotated[CurrentUser, require_permissions("admin:write")],
) -> dict[str, str]:
    """Trigger a maintenance task."""
    logger.info("maintenance_triggered task=%s by_user=%s", task, user.user_id)

    # In production, this would enqueue Celery tasks
    allowed_tasks = ["cleanup", "cache_clear", "stats_recalculation"]

    if task not in allowed_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown task '{task}'. Allowed: {allowed_tasks}",
        )

    return {"message": f"Maintenance task '{task}' has been triggered", "task": task}


class TokenConfigResponse(BaseModel):
    """Token configuration response."""

    access_token_expire_minutes: int = Field(
        ..., description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        ..., description="Refresh token expiration in days"
    )
    confirmation_token_expire_minutes: int = Field(
        ..., description="Confirmation token expiration in minutes"
    )
    algorithm: str = Field(..., description="JWT algorithm used")


class AdminTokenValidationRequest(BaseModel):
    """Admin token validation request."""

    token: str = Field(..., description="Token to validate")


class AdminTokenValidationResponse(BaseModel):
    """Admin token validation response with detailed info."""

    valid: bool = Field(..., description="Whether token is valid")
    token_type: str | None = Field(
        None, description="Token type: access, refresh, or unknown"
    )
    user_id: str | None = Field(None, description="User ID if valid")
    email: str | None = Field(None, description="User email if available")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    issued_at: str | None = Field(None, description="Token issuance timestamp (iat)")
    expires_at: str | None = Field(None, description="Token expiration timestamp (exp)")
    expires_in_seconds: int | None = Field(
        None, description="Seconds until expiration (if valid)"
    )
    error: str | None = Field(None, description="Error message if invalid")


class TokenResetResponse(BaseModel):
    """Token reset response."""

    message: str = Field(..., description="Status message")
    user_id: str = Field(..., description="User ID whose tokens were reset")
    reset_at: str = Field(..., description="Timestamp of reset")
    note: str = Field(..., description="Important note about token reset behavior")


@router.get(
    "/tokens/config",
    response_model=TokenConfigResponse,
    summary="Get token configuration",
    description="Get current JWT token expiration settings.",
    dependencies=[require_permissions("admin:read")],
)
async def get_token_config(
    rate_limit: Annotated[dict, rate_limit_admin_read],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenConfigResponse:
    """Get token expiration configuration."""
    return TokenConfigResponse(
        access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        confirmation_token_expire_minutes=settings.JWT_CONFIRMATION_TOKEN_EXPIRE_MINUTES,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post(
    "/tokens/validate",
    response_model=AdminTokenValidationResponse,
    summary="Validate token (admin detailed view)",
    description="Validate any token and return detailed information including permissions and expiration.",
    dependencies=[require_permissions("admin:read")],
)
async def admin_validate_token(
    request: AdminTokenValidationRequest,
    rate_limit: Annotated[dict, rate_limit_admin_read],
    admin_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> AdminTokenValidationResponse:
    """Validate a token with detailed admin info.

    Logs the validation attempt for audit purposes.
    """
    from datetime import UTC, datetime

    from app.core.security.jwt_service import decode_token

    logger.info("admin_token_validation by_admin=%s", admin_user.user_id)

    try:
        payload = decode_token(request.token)

        # Calculate expires_in if exp is present
        expires_in = None
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            now = datetime.now(UTC)
            exp_dt = datetime.fromtimestamp(exp_timestamp, tz=UTC)
            expires_in = int((exp_dt - now).total_seconds())
            if expires_in < 0:
                expires_in = 0

        return AdminTokenValidationResponse(
            valid=True,
            token_type=payload.get("type", "unknown"),
            user_id=payload.get("sub"),
            email=payload.get("email"),
            permissions=payload.get("permissions", []),
            issued_at=str(payload.get("iat")),
            expires_at=str(payload.get("exp")),
            expires_in_seconds=expires_in,
        )
    except Exception as exc:
        return AdminTokenValidationResponse(
            valid=False,
            error=str(exc),
        )


@router.post(
    "/users/{user_id}/tokens/reset",
    response_model=TokenResetResponse,
    summary="Reset user tokens",
    description="Force reset/invalidate all tokens for a specific user. "
    "Note: Stateless JWT tokens cannot be truly revoked server-side without a blacklist.",
    dependencies=[require_permissions("admin:write")],
)
async def reset_user_tokens(
    user_id: str,
    rate_limit: Annotated[dict, rate_limit_admin_write],
    admin_user: Annotated[CurrentUser, Depends(get_current_user)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> TokenResetResponse:
    """Reset tokens for a specific user.

    Since JWT is stateless, this marks the user for token reset in the in-memory
    store. Clients should discard their tokens and re-authenticate.
    In production, implement a token blacklist (e.g., Redis) for true revocation.
    """
    from datetime import UTC, datetime

    users = _get_users_store()

    user = users.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    # Record the reset timestamp
    now = datetime.now(UTC)
    reset_timestamp = now.isoformat()

    # Mark user with token reset requirement
    user["token_reset_at"] = reset_timestamp
    user["requires_reauth"] = True

    logger.info(
        "user_tokens_reset user_id=%s by_admin=%s tenant=%s",
        user_id,
        admin_user.user_id,
        tenant_id,
    )

    return TokenResetResponse(
        message=f"Tokens for user '{user_id}' have been marked for reset",
        user_id=user_id,
        reset_at=reset_timestamp,
        note="JWT is stateless - tokens remain valid until expiry. "
        "Client must discard tokens and re-authenticate. "
        "Consider implementing token blacklist (Redis) for production.",
    )
