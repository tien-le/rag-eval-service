"""Stateless JWT token creation and verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

import jwt

from app.core.config.settings import Settings, get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError


class JWTService(Protocol):
    """Protocol for JWT service."""

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate a JWT token and return its payload."""
        ...

    async def create_access_token(
        self, user_id: UUID, extra_claims: dict[str, Any] | None = None
    ) -> str:
        """Create a new access token."""
        ...


class JWTServiceImpl:
    """JWT service implementation."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate a JWT token and return its payload."""
        return decode_token(token)

    async def create_access_token(
        self, user_id: UUID, extra_claims: dict[str, Any] | None = None
    ) -> str:
        """Create a new access token."""
        return create_access_token(user_id, extra_claims)


_jwt_service: JWTServiceImpl | None = None


def get_jwt_service() -> JWTService:
    """Get JWT service singleton."""
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JWTServiceImpl()
    return _jwt_service


def create_access_token(
    user_id: UUID, extra_claims: dict[str, Any] | None = None
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError() from exc


def verify_access_token(token: str) -> UUID:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise InvalidTokenError()
    return UUID(payload["sub"])


def verify_refresh_token(token: str) -> UUID:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise InvalidTokenError()
    return UUID(payload["sub"])
