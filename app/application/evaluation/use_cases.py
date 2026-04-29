"""Application use cases for evaluation flows."""

from collections.abc import Sequence

from app.domain.evaluation.entities import EvaluationInput, EvaluationResult
from app.domain.evaluation.ports import EvaluatorPort, EventPublisherPort


class EvaluateAnswerUseCase:
    """Application service that orchestrates evaluation and emits domain events."""

    def __init__(self, evaluator: EvaluatorPort, event_publisher: EventPublisherPort) -> None:
        self._evaluator = evaluator
        self._event_publisher = event_publisher

    def execute(self, evaluation_input: EvaluationInput, metrics: Sequence[str]) -> EvaluationResult:
        """Execute evaluation and publish success/failure events."""
        try:
            result = self._evaluator.evaluate(evaluation_input=evaluation_input, metrics=metrics)
            self._event_publisher.publish(
                event_name="evaluation.completed",
                payload={
                    "request_id": evaluation_input.request_id,
                    "question": evaluation_input.question,
                    "scores": [{s.metric_name: s.value} for s in result.scores],
                },
            )
            return result
        except Exception as exc:
            self._event_publisher.publish(
                event_name="evaluation.failed",
                payload={
                    "request_id": evaluation_input.request_id,
                    "question": evaluation_input.question,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
            raise
