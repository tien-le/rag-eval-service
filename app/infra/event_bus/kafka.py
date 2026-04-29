"""Kafka event publisher — used by v2 (100K RPM) for high-throughput event streaming.

Requires: aiokafka  (add to requirements.txt if not present)
Enable:   KAFKA_ENABLED=true + KAFKA_BOOTSTRAP_SERVERS=<host:port>
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

try:
    from aiokafka import AIOKafkaProducer

    _AIOKAFKA_AVAILABLE = True
except ImportError:
    _AIOKAFKA_AVAILABLE = False
    AIOKafkaProducer = None  # type: ignore[assignment,misc]


class KafkaPublisher:
    """Idempotent, acks=all Kafka producer.

    Call ``await start()`` before use and ``await stop()`` on shutdown.
    Raises ``RuntimeError`` if aiokafka is not installed or if publish is
    called before start().
    """

    def __init__(self, bootstrap_servers: str) -> None:
        if not _AIOKAFKA_AVAILABLE:
            raise RuntimeError(
                "aiokafka is not installed. Add it to requirements.txt to use v2 Kafka publishing."
            )
        self._bootstrap = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            value_serializer=lambda v: json.dumps(v).encode(),
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=10_000,
        )
        await self._producer.start()
        logger.info("kafka_publisher.started bootstrap=%s", self._bootstrap)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("kafka_publisher.stopped")

    async def publish(self, topic: str, payload: dict) -> None:
        if not self._producer:
            raise RuntimeError("KafkaPublisher not started — call await start() first")
        await self._producer.send_and_wait(topic, payload)
