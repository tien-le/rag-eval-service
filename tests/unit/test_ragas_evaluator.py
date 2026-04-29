"""Tests for EvaluationService (EvaluatorPort implementation)."""

import unittest

from app.services.evaluation_service import EvaluationService


class RagasEvaluatorTests(unittest.TestCase):
    def test_evaluation_service_implements_evaluator_port(self) -> None:
        """Verify EvaluationService implements EvaluatorPort."""
        service = EvaluationService(
            evaluator_llm=object(), evaluator_embeddings=object()
        )
        # Should have evaluate method from EvaluatorPort
        self.assertTrue(hasattr(service, "evaluate"))
        self.assertTrue(callable(service.evaluate))


if __name__ == "__main__":
    unittest.main()
