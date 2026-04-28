"""Exception

Usage:
    from app.core.config.exceptions import NotFoundError, AlreadyExistsError
    raise NotFoundError("User", str(user_id))
    raise AlreadyExistsError("User", email)
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

    def __init__(
        self,
        detail: str = "An unexpected error occurred.",
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail
        self.extra = extra or {}
        super().__init__(detail)


class AuthenticationError(AppException):
    code = "AUTHENTICATION_ERROR"
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail: str = "Could not validate credentials.") -> None:
        super().__init__(detail)


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        super().__init__("Incorrect email or password.")


class TokenExpiredError(AuthenticationError):
    code = "TOKEN_EXPIRED"

    def __init__(self) -> None:
        super().__init__("Token has expired.")


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"

    def __init__(self) -> None:
        super().__init__("Token is invalid or malformed.")


class InsufficientPermissionsError(AppException):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, detail: str = "You do not have permission.") -> None:
        super().__init__(detail)


class NotFoundError(AppException):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(
        self, resource: str = "Resource", identifier: str | None = None
    ) -> None:
        detail = f"{resource} not found."
        if identifier:
            detail = f"{resource} '{identifier}' not found."
        super().__init__(detail)


class ConflictError(AppException):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail: str = "Conflict occurred.") -> None:
        super().__init__(detail)


class AlreadyExistsError(ConflictError):
    code = "ALREADY_EXISTS"

    def __init__(
        self, resource: str = "Resource", identifier: str | None = None
    ) -> None:
        detail = f"{resource} already exists."
        if identifier:
            detail = f"{resource} '{identifier}' already exists."
        super().__init__(detail)


class DomainValidationError(AppException):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, detail: str = "Validation failed.") -> None:
        super().__init__(detail)


class RateLimitExceededError(AppException):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, detail: str = "Rate limit exceeded. Try again later.") -> None:
        super().__init__(detail)


class AgentExecutionError(AppException):
    code = "AGENT_EXECUTION_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class LLMProviderError(AppException):
    code = "LLM_PROVIDER_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY

    def __init__(self, provider: str = "LLM", detail: str = "") -> None:
        message = (
            f"{provider} provider error." if not detail else f"{provider}: {detail}"
        )
        super().__init__(message)


class GraphCompilationError(AppException):
    code = "GRAPH_COMPILATION_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class MCPBootstrapError(GraphCompilationError):
    code = "MCP_BOOTSTRAP_ERROR"

    def __init__(self, detail: str = "Failed to bootstrap MCP tools.") -> None:
        super().__init__(detail)


class GraphNotInterruptedError(AppException):
    code = "GRAPH_NOT_INTERRUPTED"
    status_code = status.HTTP_409_CONFLICT

    def __init__(
        self, detail: str = "Graph run is not in an interrupted state."
    ) -> None:
        super().__init__(detail)


class DatabaseError(AppException):
    code = "DATABASE_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class CacheError(AppException):
    code = "CACHE_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class ExternalServiceError(AppException):
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY

    def __init__(self, service: str = "External service", detail: str = "") -> None:
        message = f"{service} is unavailable." if not detail else f"{service}: {detail}"
        super().__init__(message)


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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
