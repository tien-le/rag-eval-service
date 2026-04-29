"""Unit tests for app/infra/event_bus/kafka.py.

Tests guard clauses and error handling without requiring a real Kafka broker.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class KafkaPublisherGuardTests(unittest.TestCase):
    def test_publish_before_start_raises_runtime_error(self) -> None:
        from app.infra.event_bus.kafka import KafkaPublisher

        publisher = KafkaPublisher(bootstrap_servers="localhost:9092")
        with self.assertRaises(RuntimeError, msg="publish before start should raise"):
            asyncio.run(publisher.publish("topic", {"key": "val"}))

    def test_constructor_raises_when_aiokafka_unavailable(self) -> None:
        with patch("app.infra.event_bus.kafka._AIOKAFKA_AVAILABLE", False):
            from app.infra.event_bus.kafka import KafkaPublisher as _KP

            with self.assertRaises(RuntimeError):
                _KP(bootstrap_servers="localhost:9092")

    def test_stop_is_safe_when_not_started(self) -> None:
        from app.infra.event_bus.kafka import KafkaPublisher

        publisher = KafkaPublisher(bootstrap_servers="localhost:9092")
        asyncio.run(publisher.stop())  # must not raise


class KafkaPublisherStartStopTests(unittest.TestCase):
    def _make_mock_producer(self) -> AsyncMock:
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()
        return mock_producer

    def test_start_creates_producer(self) -> None:
        mock_producer = self._make_mock_producer()

        with patch(
            "app.infra.event_bus.kafka.AIOKafkaProducer", return_value=mock_producer
        ):
            from app.infra.event_bus.kafka import KafkaPublisher

            publisher = KafkaPublisher(bootstrap_servers="localhost:9092")
            asyncio.run(publisher.start())

        mock_producer.start.assert_called_once()

    def test_publish_calls_send_and_wait(self) -> None:
        mock_producer = self._make_mock_producer()

        with patch(
            "app.infra.event_bus.kafka.AIOKafkaProducer", return_value=mock_producer
        ):
            from app.infra.event_bus.kafka import KafkaPublisher

            publisher = KafkaPublisher(bootstrap_servers="localhost:9092")
            asyncio.run(publisher.start())
            asyncio.run(publisher.publish("eval.requested", {"job_id": "j1"}))

        mock_producer.send_and_wait.assert_called_once_with(
            "eval.requested", {"job_id": "j1"}
        )

    def test_stop_calls_producer_stop(self) -> None:
        mock_producer = self._make_mock_producer()

        with patch(
            "app.infra.event_bus.kafka.AIOKafkaProducer", return_value=mock_producer
        ):
            from app.infra.event_bus.kafka import KafkaPublisher

            publisher = KafkaPublisher(bootstrap_servers="localhost:9092")
            asyncio.run(publisher.start())
            asyncio.run(publisher.stop())

        mock_producer.stop.assert_called_once()

    def test_stop_clears_producer_reference(self) -> None:
        mock_producer = self._make_mock_producer()

        with patch(
            "app.infra.event_bus.kafka.AIOKafkaProducer", return_value=mock_producer
        ):
            from app.infra.event_bus.kafka import KafkaPublisher

            publisher = KafkaPublisher(bootstrap_servers="localhost:9092")
            asyncio.run(publisher.start())
            asyncio.run(publisher.stop())

        # After stop, publish should raise again
        with self.assertRaises(RuntimeError):
            asyncio.run(publisher.publish("topic", {}))


if __name__ == "__main__":
    unittest.main()
