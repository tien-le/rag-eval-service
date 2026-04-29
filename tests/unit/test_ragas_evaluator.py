"""Tests for Ragas evaluator adapter internals."""

import unittest

from app.services.rag_eval_service import RagasEvaluator


class RagasEvaluatorTests(unittest.TestCase):
    def test_resolve_metric_raises_for_unknown_metric(self) -> None:
        evaluator = RagasEvaluator(llm=object(), embeddings=object())

        with self.assertRaises(ValueError):
            evaluator._resolve_metric("unknown_metric")


if __name__ == "__main__":
    unittest.main()
