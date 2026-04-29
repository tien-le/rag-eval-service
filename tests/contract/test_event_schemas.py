"""Contract tests for app/infra/event_bus/events.py.

Verifies that all event dataclasses honour their public field contracts,
including required fields, auto-generated defaults, and serialisability.

If an event field is renamed or removed these tests will fail before any
downstream consumer (e.g. the Kafka eval_worker) is broken.
"""

import json
from dataclasses import asdict, fields

import pytest


# ---------------------------------------------------------------------------
# Shared contract helpers
# ---------------------------------------------------------------------------


def _required_base_fields() -> set[str]:
    """Fields that every event must have."""
    return {"job_id", "event_id", "occurred_at"}


def _assert_base_contract(event) -> None:
    d = asdict(event)
    missing = _required_base_fields() - set(d.keys())
    assert not missing, f"Event missing base fields: {missing}"
    assert isinstance(d["event_id"], str) and len(d["event_id"]) == 36
    assert isinstance(d["occurred_at"], str) and "T" in d["occurred_at"]


def _assert_json_serialisable(event) -> None:
    d = asdict(event)
    json.dumps(d)  # raises TypeError if not serialisable


# ---------------------------------------------------------------------------
# EvalRequestedEvent
# ---------------------------------------------------------------------------


class TestEvalRequestedEvent:
    def _make(self, **overrides) -> object:
        from app.infra.event_bus.events import EvalRequestedEvent

        defaults = {
            "job_id": "job-1",
            "eval_type": "single_turn",
            "eval_input": {"user_input": "Q", "metric_names": ["faithfulness"]},
        }
        return EvalRequestedEvent(**{**defaults, **overrides})

    def test_base_contract(self):
        _assert_base_contract(self._make())

    def test_json_serialisable(self):
        _assert_json_serialisable(self._make())

    def test_eval_type_field(self):
        event = self._make(eval_type="multi_turn")
        assert event.eval_type == "multi_turn"

    def test_eval_input_field(self):
        event = self._make(eval_input={"user_input": "test", "metric_names": ["ctx"]})
        assert event.eval_input["user_input"] == "test"

    def test_auto_generated_ids_are_unique(self):
        e1 = self._make()
        e2 = self._make()
        assert e1.event_id != e2.event_id

    def test_asdict_has_all_expected_keys(self):
        d = asdict(self._make())
        assert set(d.keys()) == {"job_id", "eval_type", "eval_input", "event_id", "occurred_at"}


# ---------------------------------------------------------------------------
# EvalCompletedEvent
# ---------------------------------------------------------------------------


class TestEvalCompletedEvent:
    def _make(self, **overrides) -> object:
        from app.infra.event_bus.events import EvalCompletedEvent

        defaults = {"job_id": "job-2", "result": {"scores": {"faithfulness": 0.9}}}
        return EvalCompletedEvent(**{**defaults, **overrides})

    def test_base_contract(self):
        _assert_base_contract(self._make())

    def test_json_serialisable(self):
        _assert_json_serialisable(self._make())

    def test_result_field_preserved(self):
        event = self._make(result={"scores": {"context_precision": 0.85}})
        assert event.result["scores"]["context_precision"] == 0.85

    def test_asdict_has_result_key(self):
        d = asdict(self._make())
        assert "result" in d

    def test_result_with_empty_scores_is_valid(self):
        event = self._make(result={"scores": {}})
        assert event.result["scores"] == {}


# ---------------------------------------------------------------------------
# EvalFailedEvent
# ---------------------------------------------------------------------------


class TestEvalFailedEvent:
    def _make(self, **overrides) -> object:
        from app.infra.event_bus.events import EvalFailedEvent

        defaults = {"job_id": "job-3", "error": "timeout after 30s"}
        return EvalFailedEvent(**{**defaults, **overrides})

    def test_base_contract(self):
        _assert_base_contract(self._make())

    def test_json_serialisable(self):
        _assert_json_serialisable(self._make())

    def test_error_field_preserved(self):
        event = self._make(error="connection refused")
        assert event.error == "connection refused"

    def test_asdict_has_error_key(self):
        d = asdict(self._make())
        assert "error" in d


# ---------------------------------------------------------------------------
# EvalStartedEvent
# ---------------------------------------------------------------------------


class TestEvalStartedEvent:
    def test_base_contract(self):
        from app.infra.event_bus.events import EvalStartedEvent

        _assert_base_contract(EvalStartedEvent(job_id="job-4"))

    def test_json_serialisable(self):
        from app.infra.event_bus.events import EvalStartedEvent

        _assert_json_serialisable(EvalStartedEvent(job_id="job-4"))


# ---------------------------------------------------------------------------
# Cross-event invariants
# ---------------------------------------------------------------------------


class TestEventCrossInvariants:
    def test_all_events_share_base_fields(self):
        from app.infra.event_bus.events import (
            EvalCompletedEvent,
            EvalFailedEvent,
            EvalRequestedEvent,
            EvalStartedEvent,
        )

        events = [
            EvalRequestedEvent(job_id="j", eval_type="single_turn", eval_input={}),
            EvalStartedEvent(job_id="j"),
            EvalCompletedEvent(job_id="j", result={}),
            EvalFailedEvent(job_id="j", error="err"),
        ]
        for event in events:
            d = asdict(event)
            for required in ("job_id", "event_id", "occurred_at"):
                assert required in d, f"{type(event).__name__} missing field '{required}'"

    def test_distinct_events_have_distinct_event_ids(self):
        from app.infra.event_bus.events import EvalCompletedEvent, EvalFailedEvent

        e1 = EvalCompletedEvent(job_id="j", result={})
        e2 = EvalFailedEvent(job_id="j", error="err")
        assert e1.event_id != e2.event_id
