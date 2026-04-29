"""Unit tests for app/infra/event_bus/events.py.

Verifies that event dataclasses have the correct fields, auto-generate
defaults (event_id, occurred_at), and are serialisable via dataclasses.asdict().
"""

import unittest
from dataclasses import asdict


class EvalRequestedEventTests(unittest.TestCase):
    def _make(self, **overrides) -> object:
        from app.infra.event_bus.events import EvalRequestedEvent

        defaults = dict(
            job_id="job-1",
            eval_type="single_turn",
            eval_input={"user_input": "Q", "metric_names": ["faithfulness"]},
        )
        return EvalRequestedEvent(**{**defaults, **overrides})

    def test_required_fields_present(self) -> None:
        event = self._make()
        self.assertEqual(event.job_id, "job-1")
        self.assertEqual(event.eval_type, "single_turn")
        self.assertIn("user_input", event.eval_input)

    def test_event_id_is_auto_generated_uuid(self) -> None:
        event = self._make()
        self.assertIsInstance(event.event_id, str)
        self.assertEqual(len(event.event_id), 36)  # UUID4

    def test_occurred_at_is_iso_string(self) -> None:
        event = self._make()
        self.assertIsInstance(event.occurred_at, str)
        self.assertIn("T", event.occurred_at)

    def test_two_events_have_different_event_ids(self) -> None:
        e1 = self._make()
        e2 = self._make()
        self.assertNotEqual(e1.event_id, e2.event_id)

    def test_asdict_is_json_serialisable(self) -> None:
        import json

        event = self._make()
        d = asdict(event)
        serialised = json.dumps(d)  # must not raise
        self.assertIn("job_id", serialised)


class EvalCompletedEventTests(unittest.TestCase):
    def test_required_fields(self) -> None:
        from app.infra.event_bus.events import EvalCompletedEvent

        event = EvalCompletedEvent(
            job_id="job-2",
            result={"scores": {"faithfulness": 0.95}},
        )
        self.assertEqual(event.job_id, "job-2")
        self.assertEqual(event.result["scores"]["faithfulness"], 0.95)
        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.occurred_at)

    def test_asdict_includes_result(self) -> None:
        from app.infra.event_bus.events import EvalCompletedEvent

        event = EvalCompletedEvent(job_id="j", result={"scores": {}})
        d = asdict(event)
        self.assertIn("result", d)
        self.assertIn("job_id", d)


class EvalFailedEventTests(unittest.TestCase):
    def test_required_fields(self) -> None:
        from app.infra.event_bus.events import EvalFailedEvent

        event = EvalFailedEvent(job_id="job-3", error="timeout after 30s")
        self.assertEqual(event.job_id, "job-3")
        self.assertEqual(event.error, "timeout after 30s")
        self.assertIsNotNone(event.event_id)

    def test_asdict_includes_error(self) -> None:
        from app.infra.event_bus.events import EvalFailedEvent

        d = asdict(EvalFailedEvent(job_id="j", error="err"))
        self.assertIn("error", d)


class EvalStartedEventTests(unittest.TestCase):
    def test_only_requires_job_id(self) -> None:
        from app.infra.event_bus.events import EvalStartedEvent

        event = EvalStartedEvent(job_id="job-4")
        self.assertEqual(event.job_id, "job-4")
        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.occurred_at)


if __name__ == "__main__":
    unittest.main()
