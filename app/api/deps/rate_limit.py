"""Rate limiting dependencies for FastAPI."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from app.core.config.logging import get_logger
from app.core.config.settings import Settings, get_settings

logger = get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Raised when rate limit is exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"},
        )


class RateLimiter:
    """Rate limiter using token bucket algorithm."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int | None = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute

    async def is_allowed(
        self,
        key: str,
        redis_client: Any | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed under rate limit.

        Args:
            key: Rate limit key (e.g., "tenant:{id}:endpoint")
            redis_client: Optional Redis client for distributed rate limiting

        Returns:
            Tuple of (allowed, metadata)
        """
        # TODO: Implement Redis-based token bucket
        # For now, return always allowed with mock metadata
        return True, {
            "limit": self.requests_per_minute,
            "remaining": self.requests_per_minute - 1,
            "reset_after": 60,
        }


class RateLimitDep:
    """Rate limiting dependency for endpoints."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        key_func: str = "ip",  # "ip", "tenant", "user", "api_key"
    ):
        self.requests_per_minute = requests_per_minute
        self.key_func = key_func
        self._limiter = RateLimiter(requests_per_minute)

    async def __call__(
        self,
        request: Request,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> dict[str, Any]:
        """Apply rate limiting and return rate limit info."""
        key = self._get_key(request)

        # Skip rate limiting in development if configured
        if not settings.is_production and getattr(
            settings, "DISABLE_RATE_LIMIT", False
        ):
            return {
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute,
                "window": "1m",
            }

        try:
            from app.infra.cache.redis_client import get_redis_client

            redis_client = await get_redis_client()
            allowed, metadata = await self._limiter.is_allowed(key, redis_client)
        except Exception as e:
            logger.warning("rate_limit_check_failed error=%s", str(e))
            # Fail open if rate limiting service is unavailable
            allowed = True
            metadata = {"limit": self.requests_per_minute, "remaining": -1}

        if not allowed:
            logger.warning("rate_limit_exceeded key=%s", key)
            raise RateLimitExceeded()

        return {
            "limit": metadata.get("limit", self.requests_per_minute),
            "remaining": metadata.get("remaining", 0),
            "window": "1m",
        }

    def _get_key(self, request: Request) -> str:
        """Generate rate limit key based on configured strategy."""
        if self.key_func == "ip":
            client_host = request.client.host if request.client else "unknown"
            return f"rate_limit:ip:{client_host}:{request.url.path}"

        elif self.key_func == "tenant":
            tenant_id = getattr(request.state, "tenant_id", "unknown")
            return f"rate_limit:tenant:{tenant_id}:{request.url.path}"

        elif self.key_func == "user":
            user_id = getattr(request.state, "user_id", "anonymous")
            return f"rate_limit:user:{user_id}:{request.url.path}"

        elif self.key_func == "api_key":
            api_key = request.headers.get("X-API-Key", "unknown")
            return f"rate_limit:api_key:{api_key}:{request.url.path}"

        return f"rate_limit:default:{request.url.path}"


def rate_limit_dependency(
    requests_per_minute: int = 60,
    key_func: str = "ip",
):
    """Create a rate limiting dependency.

    Usage:
        @router.post("/eval")
        async def evaluate(
            rate_limit: Annotated[dict, Depends(rate_limit_dependency(100, "tenant"))]
        ):
            ...
    """
    return Depends(RateLimitDep(requests_per_minute, key_func))


# Predefined rate limit configurations
rate_limit_by_ip = rate_limit_dependency(60, "ip")
rate_limit_by_tenant = rate_limit_dependency(1000, "tenant")
rate_limit_by_user = rate_limit_dependency(100, "user")
rate_limit_by_api_key = rate_limit_dependency(10000, "api_key")

# Evaluation-specific limits
rate_limit_ragas_expensive = rate_limit_dependency(
    10, "tenant"
)  # LLM calls - expensive
rate_limit_ragas_async = rate_limit_dependency(100, "tenant")  # Async enqueue - cheap
rate_limit_classification = rate_limit_dependency(100, "ip")  # Sync - moderate
rate_limit_metrics_catalog = rate_limit_dependency(1000, "ip")  # Cheap read

# Auth-specific limits
rate_limit_auth_login = rate_limit_dependency(5, "ip")  # Strict - prevent brute force
rate_limit_auth_normal = rate_limit_dependency(60, "ip")  # Normal auth operations

# Admin limits
rate_limit_admin_write = rate_limit_dependency(30, "user")  # Write operations
rate_limit_admin_read = rate_limit_dependency(100, "user")  # Read operations

# Job polling limits
rate_limit_job_poll = rate_limit_dependency(300, "ip")  # Job status polling


class TenantQuotaChecker:
    """Check tenant quota limits."""

    async def check_quota(
        self,
        tenant_id: str,
        resource: str,
        increment: int = 1,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if tenant has quota available.

        Args:
            tenant_id: Tenant identifier
            resource: Resource type (e.g., "evaluations", "workflows")
            increment: Amount to increment

        Returns:
            Tuple of (allowed, quota_info)
        """
        # TODO: Implement quota checking with Redis/DB
        # For now, always allow
        return True, {
            "resource": resource,
            "used": 0,
            "limit": 1000,
            "remaining": 1000,
        }

    async def increment_usage(
        self,
        tenant_id: str,
        resource: str,
        amount: int = 1,
    ) -> None:
        """Increment tenant resource usage."""
        # TODO: Implement usage tracking
        logger.debug(
            "quota_increment tenant=%s resource=%s amount=%d",
            tenant_id,
            resource,
            amount,
        )


async def get_quota_checker() -> TenantQuotaChecker:
    """Get quota checker instance."""
    return TenantQuotaChecker()
