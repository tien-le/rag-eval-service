"""Tracing dependencies for FastAPI."""

from typing import Annotated, Any
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Header, Request

# Context variables for trace propagation
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
span_id_var: ContextVar[str] = ContextVar("span_id", default="")


def get_trace_id(request: Request) -> str:
    """Get trace ID from request state or generate new one.

    Args:
        request: FastAPI request

    Returns:
        Trace ID string
    """
    # Try to get from request state (set by middleware)
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id:
        return trace_id

    # Try to get from context var
    trace_id = trace_id_var.get()
    if trace_id:
        return trace_id

    # Generate new trace ID
    return str(uuid4())


def get_correlation_id(
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> str | None:
    """Get correlation ID from header or context.

    Args:
        x_correlation_id: Correlation ID from request header

    Returns:
        Correlation ID or None
    """
    if x_correlation_id:
        return x_correlation_id

    return correlation_id_var.get()


class TracingContext:
    """Tracing context for request handling."""

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        correlation_id: str | None = None,
        parent_span_id: str | None = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.correlation_id = correlation_id
        self.parent_span_id = parent_span_id
        self._token_trace_id: Any | None = None
        self._token_span_id: Any | None = None
        self._token_corr_id: Any | None = None

    def __enter__(self):
        """Enter context and set trace variables."""
        self._token_trace_id = trace_id_var.set(self.trace_id)
        self._token_span_id = span_id_var.set(self.span_id)
        if self.correlation_id:
            self._token_corr_id = correlation_id_var.set(self.correlation_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset trace variables."""
        if self._token_trace_id:
            trace_id_var.reset(self._token_trace_id)
        if self._token_span_id:
            span_id_var.reset(self._token_span_id)
        if self._token_corr_id:
            correlation_id_var.reset(self._token_corr_id)

    def to_headers(self) -> dict[str, str]:
        """Convert tracing context to HTTP headers."""
        headers = {
            "X-Trace-ID": self.trace_id,
            "traceparent": f"00-{self.trace_id.replace('-', '')}-{self.span_id}-01",
        }
        if self.correlation_id:
            headers["X-Correlation-ID"] = self.correlation_id
        return headers


def tracing_context(
    request: Request,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TracingContext:
    """Create tracing context from request.

    Args:
        request: FastAPI request
        x_correlation_id: Optional correlation ID from header

    Returns:
        TracingContext
    """
    trace_id = get_trace_id(request)
    span_id = str(uuid4())[:16]
    correlation_id = x_correlation_id or getattr(request.state, "correlation_id", None)

    return TracingContext(
        trace_id=trace_id,
        span_id=span_id,
        correlation_id=correlation_id,
    )


def get_current_trace_id() -> str:
    """Get current trace ID from context variable."""
    return trace_id_var.get() or str(uuid4())


def get_current_span_id() -> str:
    """Get current span ID from context variable."""
    return span_id_var.get() or str(uuid4())[:16]


def set_trace_context(trace_id: str, span_id: str) -> tuple[Any, Any]:
    """Set trace context variables.

    Returns:
        Tokens for resetting context
    """
    token_trace = trace_id_var.set(trace_id)
    token_span = span_id_var.set(span_id)
    return token_trace, token_span


def reset_trace_context(token_trace: Any, token_span: Any) -> None:
    """Reset trace context variables."""
    trace_id_var.reset(token_trace)
    span_id_var.reset(token_span)
