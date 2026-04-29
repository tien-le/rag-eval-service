"""Exception

Usage:
    from app.core.config.exceptions import NotFoundError, AlreadyExistsError
    raise NotFoundError("User", str(user_id))
    raise AlreadyExistsError("User", email)

    raise EmbeddingServiceError("OpenAI Embeddings", "Request timed out.")

    raise EmbeddingServiceError(
        "Qdrant embedding worker",
        "Failed to generate vectors.",
        extra={"document_id": str(document_id)},
    )

    logger.exception("Application exception: %s", exc.detail)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for application/domain exceptions."""

    code: str = "APP_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.default_detail
        self.extra = extra or {}
        super().__init__(self.detail)


class AuthenticationError(AppException):
    code = "AUTHENTICATION_ERROR"
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Could not validate credentials."


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"
    default_detail = "Incorrect email or password."


class TokenExpiredError(AuthenticationError):
    code = "TOKEN_EXPIRED"
    default_detail = "Token has expired."


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"
    default_detail = "Token is invalid or malformed."


class InsufficientPermissionsError(AppException):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission."


class NotFoundError(AppException):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        detail = (
            f"{resource} '{identifier}' not found."
            if identifier
            else f"{resource} not found."
        )
        super().__init__(detail, extra=extra)


class ConflictError(AppException):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict occurred."


class AlreadyExistsError(ConflictError):
    code = "ALREADY_EXISTS"

    def __init__(
        self,
        resource: str = "Resource",
        identifier: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        detail = (
            f"{resource} '{identifier}' already exists."
            if identifier
            else f"{resource} already exists."
        )
        super().__init__(detail, extra=extra)


class DomainValidationError(AppException):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_detail = "Validation failed."


class RateLimitExceededError(AppException):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded. Try again later."


class AgentExecutionError(AppException):
    code = "AGENT_EXECUTION_ERROR"


class LLMProviderError(AppException):
    code = "LLM_PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY

    def __init__(
        self,
        provider: str = "LLM",
        detail: str = "",
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        message = (
            f"{provider} provider error." if not detail else f"{provider}: {detail}"
        )
        super().__init__(message, extra=extra)


class ExternalServiceError(AppException):
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY

    def __init__(
        self,
        service: str = "External service",
        detail: str = "",
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        message = f"{service} is unavailable." if not detail else f"{service}: {detail}"
        super().__init__(message, extra=extra)


class EmbeddingServiceError(ExternalServiceError):
    code = "EMBEDDING_SERVICE_ERROR"

    def __init__(
        self,
        provider: str = "Embedding service",
        detail: str = "",
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(provider, detail, extra=extra)


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    detail: Any,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "detail": detail,
            "path": request.url.path,
        }
    }

    if extra:
        body["error"]["extra"] = extra

    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("Application exception: %s", exc.detail, exc_info=exc)
        else:
            logger.info("Handled application exception: %s", exc.detail)

        return error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            detail=exc.detail,
            extra=exc.extra,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return error_response(
            request=request,
            status_code=exc.status_code,
            code="HTTP_ERROR",
            detail=exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="REQUEST_VALIDATION_ERROR",
            detail=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)

        return error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            detail="Internal server error.",
        )
