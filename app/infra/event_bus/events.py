"""Canonical event schemas for the internal event bus."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Eval events
# ---------------------------------------------------------------------------


@dataclass
class EvalRequestedEvent:
    """Published by the API when an async eval job is created."""

    job_id: str
    eval_type: str  # single_turn | multi_turn | classification
    eval_input: dict
    event_id: str = field(default_factory=_new_id)
    occurred_at: str = field(default_factory=_now_iso)


@dataclass
class EvalStartedEvent:
    job_id: str
    event_id: str = field(default_factory=_new_id)
    occurred_at: str = field(default_factory=_now_iso)


@dataclass
class EvalCompletedEvent:
    job_id: str
    result: dict
    event_id: str = field(default_factory=_new_id)
    occurred_at: str = field(default_factory=_now_iso)


@dataclass
class EvalFailedEvent:
    job_id: str
    error: str
    event_id: str = field(default_factory=_new_id)
    occurred_at: str = field(default_factory=_now_iso)
