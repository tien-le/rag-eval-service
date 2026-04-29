"""Authentication router for token management."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser, get_current_user
from app.core.config.logging import get_logger
from app.core.config.settings import Settings, get_settings
from app.core.security.jwt_service import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str = Field(..., description="User identifier (e.g., email or username)")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Token response with access and refresh tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshRequest(BaseModel):
    """Refresh token request payload."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenValidationRequest(BaseModel):
    """Token validation request."""

    token: str = Field(..., description="Token to validate")


class TokenValidationResponse(BaseModel):
    """Token validation response."""

    valid: bool = Field(..., description="Whether token is valid")
    user_id: str | None = Field(None, description="User ID if valid")
    expires_at: str | None = Field(None, description="Expiration timestamp")
    error: str | None = Field(None, description="Error message if invalid")


class UserInfoResponse(BaseModel):
    """Current user info response."""

    user_id: str | None = Field(None, description="User ID")
    email: str | None = Field(None, description="User email")
    permissions: list[str] = Field(default_factory=list, description="User permissions")


def _authenticate_user(
    username: str, password: str, settings: Settings
) -> dict[str, Any] | None:
    """Authenticate user and return user data if valid.

    Checks both env-based admin credentials and in-memory user store.
    In production, this should check against a user database.
    """
    # Check admin credentials from env first
    admin_user = getattr(settings, "ADMIN_USERNAME", "admin")
    admin_pass_obj = getattr(settings, "ADMIN_PASSWORD", None)
    admin_pass = admin_pass_obj.get_secret_value() if admin_pass_obj else "admin"

    if username == admin_user and password == admin_pass:
        # Return admin user data
        return {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "email": f"{username}@local",
            "permissions": ["admin:*", "eval:*", "workflow:*"],
        }

    # Check in-memory user store (users created via admin API)
    from app.api.routers.admin_router import _get_users_store, _verify_password

    users = _get_users_store()
    for user_data in users.values():
        if user_data["username"] == username and _verify_password(
            password, user_data["password_hash"]
        ):
            return {
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "permissions": user_data.get(
                    "permissions", ["eval:read", "workflow:read"]
                ),
            }

    return None


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and get tokens",
    description="Authenticate with username/password and receive access/refresh tokens.",
)
async def login(
    request: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Authenticate user and issue JWT tokens."""
    from uuid import UUID

    user_data = _authenticate_user(request.username, request.password, settings)

    if not user_data:
        logger.warning("login_failed username=%s", request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens with user info from user_data
    extra_claims = {
        "email": user_data["email"],
        "permissions": user_data["permissions"],
    }

    user_id = UUID(user_data["user_id"])
    access_token = create_access_token(user_id, extra_claims)
    refresh_token = create_refresh_token(user_id)

    logger.info("login_success user_id=%s", user_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Get access token (OAuth2 style)",
    description="OAuth2-compatible token endpoint for client credentials flow.",
)
async def get_token(
    request: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """OAuth2-style token endpoint (same as login)."""
    return await login(request, settings)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Use a valid refresh token to get a new access token.",
)
async def refresh_token(
    request: RefreshRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Refresh access token using a valid refresh token."""
    try:
        user_id = verify_refresh_token(request.refresh_token)
    except Exception as exc:
        logger.warning("refresh_token_failed error=%s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Get user info (in production, fetch from DB)
    extra_claims = {
        "email": "admin@local",
        "permissions": ["admin:*", "eval:*", "workflow:*"],
    }

    # Issue new tokens
    new_access_token = create_access_token(user_id, extra_claims)
    new_refresh_token = create_refresh_token(user_id)

    logger.info("token_refresh_success user_id=%s", user_id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/validate",
    response_model=TokenValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a token",
    description="Check if a token is valid and return its details.",
)
async def validate_token(
    request: TokenValidationRequest,
) -> TokenValidationResponse:
    """Validate a JWT token and return its status."""
    from app.core.security.jwt_service import decode_token

    try:
        payload = decode_token(request.token)
        return TokenValidationResponse(
            valid=True,
            user_id=payload.get("sub"),
            expires_at=str(payload.get("exp")),
        )
    except Exception as exc:
        return TokenValidationResponse(
            valid=False,
            error=str(exc),
        )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user info",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> UserInfoResponse:
    """Get information about the authenticated user."""
    return UserInfoResponse(
        user_id=user.user_id,
        email=user.email,
        permissions=user.permissions,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout (client-side token discard)",
    description="Invalidate tokens on client side. Server-side token revocation not implemented.",
)
async def logout(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    """Logout endpoint - tokens should be discarded by client.

    Note: For true server-side token invalidation, a token blacklist would be needed.
    """
    logger.info("logout user_id=%s", user.user_id)
    return {"message": "Successfully logged out. Discard tokens on client side."}
