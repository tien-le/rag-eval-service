"""Tests for evaluation service orchestration."""

import asyncio
import unittest

from app.infra.event_bus.in_memory_event_bus import InMemoryEventBus
from app.services.evaluation_service import EvaluationService


class _FakeRagasAdapter:
    async def run_single_turn(self, **kwargs):
        _ = kwargs
        return {"faithfulness": 0.88}


class EvaluationServiceTests(unittest.TestCase):
    def test_metric_catalog_contains_accuracy(self) -> None:
        service = EvaluationService(ragas_adapter=_FakeRagasAdapter(), event_bus=InMemoryEventBus())
        catalog = service.metric_catalog()
        self.assertTrue(any(metric["name"] == "accuracy" for metric in catalog))
        self.assertTrue(any(metric["name"] == "context_utilization" for metric in catalog))
        self.assertTrue(any(metric["name"] == "tool_call_accuracy" for metric in catalog))

    def test_evaluate_classification_emits_event(self) -> None:
        bus = InMemoryEventBus()
        service = EvaluationService(ragas_adapter=_FakeRagasAdapter(), event_bus=bus)
        result = service.evaluate_classification(
            actual=["positive", "negative"],
            predicted=["positive", "negative"],
            positive_label="positive",
        )
        self.assertAlmostEqual(result["summary"]["accuracy"], 1.0)
        self.assertEqual(bus.events[0]["event_name"], "evaluation.classification.completed")

    def test_evaluate_ragas_single_turn_emits_event(self) -> None:
        bus = InMemoryEventBus()
        service = EvaluationService(ragas_adapter=_FakeRagasAdapter(), event_bus=bus)
        result = asyncio.run(
            service.evaluate_ragas_single_turn(
                user_input="Q",
                response="A",
                retrieved_contexts=["ctx"],
                reference_contexts=["ctx"],
                retrieved_context_ids=["doc_1"],
                reference_context_ids=["doc_1"],
                reference="ref",
                metric_names=["faithfulness"],
            )
        )
        self.assertEqual(result["scores"]["faithfulness"], 0.88)
        self.assertEqual(bus.events[0]["event_name"], "evaluation.ragas.completed")


if __name__ == "__main__":
    unittest.main()
