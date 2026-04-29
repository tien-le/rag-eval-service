"""Abstract event publisher protocol — implemented by Redis Streams and Kafka adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EventPublisher(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def publish(self, topic: str, payload: dict) -> None: ...
