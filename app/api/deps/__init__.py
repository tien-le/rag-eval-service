"""API dependencies for FastAPI routers."""

from app.api.deps.auth import get_current_user, require_permissions
from app.api.deps.pagination import PaginationParams, get_pagination
from app.api.deps.rate_limit import RateLimitDep, rate_limit_dependency
from app.api.deps.tenant import TenantContext, get_tenant_context, get_tenant_id
from app.api.deps.tracing import get_trace_id, tracing_context

__all__ = [
    "get_current_user",
    "require_permissions",
    "PaginationParams",
    "get_pagination",
    "RateLimitDep",
    "rate_limit_dependency",
    "TenantContext",
    "get_tenant_context",
    "get_tenant_id",
    "get_trace_id",
    "tracing_context",
]
