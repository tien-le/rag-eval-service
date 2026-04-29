"""Simple in-memory event bus implementation."""

from app.domain.evaluation.ports import EventPublisherPort


class InMemoryEventBus(EventPublisherPort):
    """In-memory event publisher for local/dev/testing use."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish(self, event_name: str, payload: dict) -> None:
        self.events.append({"event_name": event_name, "payload": payload})
