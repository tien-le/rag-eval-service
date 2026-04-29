"""Evaluation service orchestration for API layer."""

from dataclasses import asdict
from typing import Any

from app.core.config.metric_catalog import METRIC_CATALOG
from app.infra.evaluation.ragas_adapter import RagasAdapter
from app.infra.event_bus.in_memory_event_bus import InMemoryEventBus
from app.utils.evaluation_metrics import class_distribution, classification_summary


class EvaluationService:
    """Coordinates classification metrics and ragas scoring."""

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

    def metric_catalog(self) -> list[dict]:
        return [asdict(metric) for metric in METRIC_CATALOG]

    def evaluator_dependencies(self) -> dict[str, Any | None]:
        return {
            "llm": self._evaluator_llm,
            "embeddings": self._evaluator_embeddings,
        }

    def evaluate_classification(self, *, actual: list[str], predicted: list[str], positive_label: str) -> dict:
        summary = classification_summary(actual=actual, predicted=predicted, positive_label=positive_label)
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
        reference_contexts: list[str] | None,
        retrieved_context_ids: list[str] | None,
        reference_context_ids: list[str] | None,
        reference: str | None,
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
            llm=llm if llm is not None else self._evaluator_llm,
            embeddings=embeddings if embeddings is not None else self._evaluator_embeddings,
        )
        self._event_bus.publish(
            "evaluation.ragas.completed",
            {
                "metrics": metric_names,
                "score_count": len(scores),
            },
        )
        return {"scores": scores}

