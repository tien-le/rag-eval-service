"""Tests for offline metric utilities."""

import unittest

from app.utils.evaluation_metrics import classification_summary


class EvaluationMetricsTests(unittest.TestCase):
    def test_classification_summary_computes_expected_values(self) -> None:
        summary = classification_summary(
            actual=["positive", "negative", "positive", "negative"],
            predicted=["positive", "positive", "positive", "negative"],
            positive_label="positive",
        )
        self.assertEqual(summary["samples"], 4)
        self.assertAlmostEqual(summary["accuracy"], 0.75)
        self.assertAlmostEqual(summary["precision"], 2 / 3)
        self.assertAlmostEqual(summary["recall"], 1.0)
        self.assertEqual(summary["tp"], 2)
        self.assertEqual(summary["fp"], 1)
        self.assertEqual(summary["tn"], 1)
        self.assertEqual(summary["fn"], 0)


if __name__ == "__main__":
    unittest.main()
