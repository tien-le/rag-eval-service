"""Domain entities for evaluation workflows."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationInput:
    """Input value object for a single evaluation request."""

    question: str
    contexts: list[str]
    answer: str
    ground_truth: str
    request_id: str | None = None


@dataclass(frozen=True)
class EvaluationScore:
    """Metric score returned by an evaluator."""

    metric_name: str
    value: float


@dataclass(frozen=True)
class EvaluationResult:
    """Result aggregate returned to application layer."""

    scores: list[EvaluationScore]
    raw_payload: dict[str, Any]
