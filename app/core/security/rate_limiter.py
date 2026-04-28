"""Rate-limiting middleware using SlowAPI."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config.settings import get_settings

settings = get_settings()


from app.core.config import settings

# Initialize global limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{settings.RATE_LIMIT_PER_MINUTE}/minute",
        f"{settings.RATE_LIMIT_PER_HOUR}/hour",
    ]
    if settings.RATE_LIMIT_ENABLED
    else [],
)


def get_limiter() -> Limiter:
    """Get rate limiter instance.

    Returns:
        Configured Limiter instance

    Usage:
        ```python
        from app.core.rate_limit import get_limiter
        from fastapi import Request

        limiter = get_limiter()

        @router.post("/endpoint")
        @limiter.limit("5/minute")
        async def endpoint(request: Request):
            ...
        ```
    """
    return limiter
