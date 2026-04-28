"""Request-scoped context for latency correlation."""

from contextvars import ContextVar, Token

correlation_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> Token[str | None]:
    return correlation_id.set(request_id)


def get_request_id() -> str | None:
    if correlation_id:
        return correlation_id.get()
    return None


def reset_request_id(token: Token[str | None]) -> None:
    correlation_id.reset(token)
