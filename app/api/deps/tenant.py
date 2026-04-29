"""Tenant context dependencies for FastAPI."""

from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config.logging import get_logger
from app.core.config.settings import Settings, get_settings

logger = get_logger(__name__)


class TenantContext:
    """Tenant context for multi-tenant operations."""

    def __init__(
        self,
        tenant_id: str,
        tenant_name: str | None = None,
        plan: str = "default",
        quota_limits: dict[str, Any] | None = None,
        features: list[str] | None = None,
    ):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.plan = plan
        self.quota_limits = quota_limits or {}
        self.features = features or []

    def has_feature(self, feature: str) -> bool:
        """Check if tenant has access to a specific feature."""
        return feature in self.features or "*" in self.features

    def get_quota(self, resource: str, default: int = 1000) -> int:
        """Get quota limit for a specific resource."""
        return self.quota_limits.get(resource, default)


def get_tenant_from_header(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
) -> str | None:
    """Extract tenant ID from request header."""
    return x_tenant_id


async def get_tenant_context(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    tenant_id: Annotated[str | None, Depends(get_tenant_from_header)] = None,
) -> TenantContext:
    """Resolve tenant context from request.

    Tenant resolution order:
    1. X-Tenant-ID header
    2. JWT token claims (if authenticated)
    3. Default tenant from settings

    Args:
        request: FastAPI request
        settings: Application settings
        tenant_id: Optional tenant ID from header

    Returns:
        TenantContext
    """
    # If no tenant ID in header, try to get from request state (set by auth middleware)
    if not tenant_id:
        tenant_id = getattr(request.state, "tenant_id", None)

    # Fall back to default tenant
    if not tenant_id:
        tenant_id = getattr(settings, "DEFAULT_TENANT_ID", "default")

    # In production, validate tenant exists and is active
    if settings.is_production:
        # TODO: Validate against tenant registry
        pass

    # Load tenant configuration (in production, fetch from DB/cache)
    tenant_config = _load_tenant_config(tenant_id, settings)

    return TenantContext(
        tenant_id=tenant_id,
        tenant_name=tenant_config.get("name"),
        plan=tenant_config.get("plan", "default"),
        quota_limits=tenant_config.get("quotas", {}),
        features=tenant_config.get("features", []),
    )


def _load_tenant_config(tenant_id: str, settings: Settings) -> dict[str, Any]:
    """Load tenant configuration.

    In production, this should fetch from a tenant registry or database.
    For now, we use a simple in-memory lookup or default config.
    """
    # TODO: Implement proper tenant config loading from DB/cache
    default_config = {
        "name": f"Tenant {tenant_id}",
        "plan": "default",
        "quotas": {
            "evaluations_per_hour": 1000,
            "workflows_per_hour": 100,
            "llm_calls_per_hour": 10000,
        },
        "features": ["eval:read", "eval:write", "workflow:read", "workflow:write"],
    }

    # Load from settings if available
    if hasattr(settings, "TENANT_CONFIGS"):
        tenant_configs = getattr(settings, "TENANT_CONFIGS", {})
        if tenant_id in tenant_configs:
            return {**default_config, **tenant_configs[tenant_id]}

    return default_config


class RequireTenant:
    """Dependency that enforces tenant identification."""

    async def __call__(
        self,
        tenant: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        """Ensure tenant context is present."""
        if not tenant.tenant_id or tenant.tenant_id == "default":
            # In production, require explicit tenant identification
            settings = get_settings()
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant identification required (X-Tenant-ID header)",
                )

        return tenant


require_tenant = Depends(RequireTenant())


async def get_optional_tenant(
    tenant: Annotated[TenantContext | None, Depends(get_tenant_context)] = None,
) -> TenantContext | None:
    """Get tenant context if available, otherwise None."""
    return tenant


async def get_tenant_id(
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> str:
    """Get tenant ID string from tenant context.

    Args:
        tenant: Tenant context from dependency

    Returns:
        Tenant ID string
    """
    return tenant.tenant_id
