"""Redis Streams event publisher — used by v1 (1K RPM) for lightweight event streaming."""

from __future__ import annotations

import json

from app.infra.cache.redis_client import get_redis

STREAM_MAXLEN = 10_000  # cap each stream at 10 K entries (approximate)


class RedisStreamsPublisher:
    """Publishes events to Redis Streams topics.

    Lifecycle is managed by the FastAPI lifespan; no persistent connection held.
    """

    async def start(self) -> None:
        pass  # lazy — get_redis() handles pool init

    async def stop(self) -> None:
        pass

    async def publish(self, topic: str, payload: dict) -> None:
        r = await get_redis()
        await r.xadd(
            topic,
            {"data": json.dumps(payload)},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
