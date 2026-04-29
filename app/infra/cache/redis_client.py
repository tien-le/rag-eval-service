"""Redis async connection pool (shared by v1 job store, rate limiter, cache)."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config.settings import get_settings

_pool: aioredis.ConnectionPool | None = None


def _build_url() -> str:
    s = get_settings()
    if s.REDIS_URL:
        return s.REDIS_URL
    scheme = "rediss" if s.REDIS_SSL else "redis"
    auth = f":{s.REDIS_PASSWORD}@" if s.REDIS_PASSWORD else ""
    return f"{scheme}://{auth}{s.REDIS_HOST}:{s.REDIS_PORT}/{s.REDIS_DB}"


async def init_redis_pool() -> None:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(_build_url(), decode_responses=True)


async def close_redis_pool() -> None:
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        await init_redis_pool()
    return aioredis.Redis(connection_pool=_pool)
