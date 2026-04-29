"""Domain ports for dependency inversion."""

from collections.abc import Sequence
from typing import Protocol

from app.domain.evaluation.entities import EvaluationInput, EvaluationResult


class EvaluatorPort(Protocol):
    """Port for model-based evaluation providers."""

    def evaluate(self, evaluation_input: EvaluationInput, metrics: Sequence[str]) -> EvaluationResult:
        """Evaluate the input against requested metrics."""


class EventPublisherPort(Protocol):
    """Port for event-driven integration."""

    def publish(self, event_name: str, payload: dict) -> None:
        """Publish a domain event to the underlying event bus."""
