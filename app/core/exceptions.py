"""Core exceptions for the application."""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code or "app_error"
        super().__init__(message)


class InvalidTokenError(AppException):
    """Raised when a token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, "invalid_token")


class TokenExpiredError(AppException):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, "token_expired")


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "authentication_error")


class AuthorizationError(AppException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, "authorization_error")


class NotFoundError(AppException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", "not_found")


class ValidationError(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "validation_error")


class ConflictError(AppException):
    """Raised when there's a resource conflict."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, "conflict")


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "rate_limit_exceeded")


class ServiceUnavailableError(AppException):
    """Raised when a service is unavailable."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, "service_unavailable")


class LLMProviderError(AppException):
    """Raised when an LLM provider call fails."""

    def __init__(self, provider: str, message: str = "Provider error"):
        super().__init__(f"{provider}: {message}", "llm_provider_error")
