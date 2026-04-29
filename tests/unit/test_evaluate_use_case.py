"""Tests for the evaluation application use case."""

import unittest

from app.application.evaluation.use_cases import EvaluateAnswerUseCase
from app.domain.evaluation.entities import EvaluationInput, EvaluationResult, EvaluationScore


class _FakeEvaluator:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def evaluate(self, evaluation_input: EvaluationInput, metrics: list[str]) -> EvaluationResult:
        if self.should_fail:
            raise RuntimeError("evaluation failed")
        return EvaluationResult(
            scores=[EvaluationScore(metric_name=metrics[0], value=0.91)],
            raw_payload={"ok": True},
        )


class _FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, event_name: str, payload: dict) -> None:
        self.events.append((event_name, payload))


class EvaluateAnswerUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_input = EvaluationInput(
            question="What is RAG?",
            contexts=["RAG combines retrieval and generation."],
            answer="RAG uses external context for generation.",
            ground_truth="RAG uses retrieval to ground generation.",
            request_id="req-1",
        )

    def test_execute_publishes_completed_event(self) -> None:
        publisher = _FakePublisher()
        use_case = EvaluateAnswerUseCase(
            evaluator=_FakeEvaluator(should_fail=False),
            event_publisher=publisher,
        )

        result = use_case.execute(evaluation_input=self.sample_input, metrics=["answer_relevancy"])

        self.assertEqual(len(result.scores), 1)
        self.assertEqual(publisher.events[0][0], "evaluation.completed")

    def test_execute_publishes_failed_event_and_raises(self) -> None:
        publisher = _FakePublisher()
        use_case = EvaluateAnswerUseCase(
            evaluator=_FakeEvaluator(should_fail=True),
            event_publisher=publisher,
        )

        with self.assertRaises(RuntimeError):
            use_case.execute(evaluation_input=self.sample_input, metrics=["answer_relevancy"])

        self.assertEqual(publisher.events[0][0], "evaluation.failed")


if __name__ == "__main__":
    unittest.main()
