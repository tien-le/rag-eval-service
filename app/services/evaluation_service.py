"""Evaluation service orchestration for API layer."""

import asyncio
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from app.core.config.metric_catalog import METRIC_CATALOG
from app.domain.evaluation.entities import (
    EvaluationInput,
    EvaluationResult,
    EvaluationScore,
)
from app.domain.evaluation.ports import EvaluatorPort
from app.infra.evaluation.ragas_adapter import RagasAdapter
from app.infra.event_bus.in_memory_event_bus import InMemoryEventBus
from app.utils.evaluation_metrics import class_distribution, classification_summary


class EvaluationService(EvaluatorPort):
    """Coordinates classification metrics and ragas scoring.

    Implements EvaluatorPort for domain layer integration.
    """

    def __init__(
        self,
        *,
        ragas_adapter: RagasAdapter | None = None,
        event_bus: InMemoryEventBus | None = None,
        evaluator_llm: Any | None = None,
        evaluator_embeddings: Any | None = None,
    ) -> None:
        self._ragas_adapter = ragas_adapter or RagasAdapter()
        self._event_bus = event_bus or InMemoryEventBus()
        self._evaluator_llm = evaluator_llm
        self._evaluator_embeddings = evaluator_embeddings

    @property
    def llm(self) -> Any | None:
        return self._evaluator_llm

    @property
    def embeddings(self) -> Any | None:
        return self._evaluator_embeddings

    def metric_catalog(self) -> list[dict]:
        return [asdict(metric) for metric in METRIC_CATALOG]

    # --- EvaluatorPort implementation ---

    def evaluate(
        self, evaluation_input: EvaluationInput, metrics: Sequence[str]
    ) -> EvaluationResult:
        """Synchronous evaluation matching EvaluatorPort interface."""
        scores_dict = asyncio.run(
            self._ragas_adapter.run_single_turn(
                user_input=evaluation_input.question,
                response=evaluation_input.answer,
                retrieved_contexts=evaluation_input.contexts,
                reference_contexts=None,
                retrieved_context_ids=None,
                reference_context_ids=None,
                reference=evaluation_input.ground_truth,
                metric_names=list(metrics),
                llm=self._evaluator_llm,
                embeddings=self._evaluator_embeddings,
            )
        )
        scores = [
            EvaluationScore(metric_name=metric_name, value=value)
            for metric_name, value in scores_dict.items()
        ]
        return EvaluationResult(scores=scores, raw_payload=scores_dict)

    # --- Classification evaluation ---

    def evaluate_classification(
        self, *, actual: list[str], predicted: list[str], positive_label: str
    ) -> dict:
        summary = classification_summary(
            actual=actual, predicted=predicted, positive_label=positive_label
        )
        self._event_bus.publish(
            "evaluation.classification.completed",
            {
                "samples": summary["samples"],
                "positive_label": positive_label,
                "accuracy": summary["accuracy"],
            },
        )
        return {
            "summary": summary,
            "actual_distribution": class_distribution(actual),
            "predicted_distribution": class_distribution(predicted),
        }

    async def evaluate_ragas_single_turn(
        self,
        *,
        user_input: str,
        response: str,
        retrieved_contexts: list[str],
        reference_contexts: list[str] | None = None,
        retrieved_context_ids: list[str] | None = None,
        reference_context_ids: list[str] | None = None,
        reference: str | None = None,
        metric_names: list[str],
        llm: Any | None = None,
        embeddings: Any | None = None,
    ) -> dict:
        scores = await self._ragas_adapter.run_single_turn(
            user_input=user_input,
            response=response,
            retrieved_contexts=retrieved_contexts,
            reference_contexts=reference_contexts,
            retrieved_context_ids=retrieved_context_ids,
            reference_context_ids=reference_context_ids,
            reference=reference,
            metric_names=metric_names,
            llm=llm or self._evaluator_llm,
            embeddings=embeddings or self._evaluator_embeddings,
        )
        self._event_bus.publish(
            "evaluation.ragas.completed",
            {
                "metrics": metric_names,
                "score_count": len(scores),
            },
        )
        return {"scores": scores}
