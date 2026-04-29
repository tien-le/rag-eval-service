"""Ragas adapter for metric execution."""

import inspect
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config.exceptions import ExternalServiceError
from app.core.config.metric_catalog import METRIC_CATALOG


class RagasAdapter:
    """Best-effort adapter around ragas imports and execution."""

    SUPPORTED_METRICS = {
        m.name
        for m in METRIC_CATALOG
        if m.category in {"retrieval", "generation", "robustness", "agent"}
    }
    _SUPPORTED_CONSTRUCTOR_ARGS = ("llm", "embeddings")

    @classmethod
    @lru_cache(maxsize=1)
    def _load_metric_requirements_config(cls) -> dict[str, tuple[str, ...]]:
        try:
            import yaml
        except Exception:
            return {}

        config_path = (
            Path(__file__).resolve().parents[2]
            / "core"
            / "config"
            / "ragas_metric_requirements.yaml"
        )
        if not config_path.exists():
            return {}

        with config_path.open("r", encoding="utf-8") as config_file:
            raw = yaml.safe_load(config_file) or {}

        metrics = raw.get("metrics", {}) if isinstance(raw, dict) else {}
        normalized: dict[str, tuple[str, ...]] = {}
        for metric_name, metric_cfg in metrics.items():
            if not isinstance(metric_cfg, dict):
                continue
            required_args = metric_cfg.get("constructor_args", [])
            if not isinstance(required_args, list):
                continue
            normalized[metric_name] = tuple(
                arg
                for arg in required_args
                if isinstance(arg, str) and arg in cls._SUPPORTED_CONSTRUCTOR_ARGS
            )
        return normalized

    @classmethod
    def _infer_constructor_args_from_signature(
        cls, metric_class: type[Any]
    ) -> tuple[str, ...]:
        try:
            signature = inspect.signature(metric_class.__init__)
        except Exception:
            return ()
        return tuple(
            arg
            for arg in cls._SUPPORTED_CONSTRUCTOR_ARGS
            if arg in signature.parameters
        )

    @classmethod
    def required_constructor_args(cls, metric_names: Sequence[str]) -> set[str]:
        configured_requirements = cls._load_metric_requirements_config()
        required: set[str] = set()
        for metric_name in metric_names:
            required.update(configured_requirements.get(metric_name, ()))
        return required

    async def run_single_turn(
        self,
        *,
        user_input: str,
        response: str,
        retrieved_contexts: list[str],
        reference_contexts: list[str] | None,
        retrieved_context_ids: list[str] | None,
        reference_context_ids: list[str] | None,
        reference: str | None,
        metric_names: Sequence[str],
        llm: Any | None = None,
        embeddings: Any | None = None,
    ) -> dict[str, Any]:
        unsupported = [
            metric for metric in metric_names if metric not in self.SUPPORTED_METRICS
        ]
        if unsupported:
            raise ValueError(f"Unsupported ragas metrics: {unsupported}")

        try:
            from datasets import Dataset
            from ragas import SingleTurnSample, aevaluate
            from ragas import metrics as ragas_metrics
            from ragas.metrics import collections as metric_collections
            from ragas.metrics.base import Metric
        except Exception as exc:
            raise ExternalServiceError(
                "ragas", f"ragas is not available: {exc}"
            ) from exc

        def _resolve_metric_class(*class_names: str):
            for class_name in class_names:
                # Prefer ragas.metrics because aevaluate expects Metric objects.
                metric_class = getattr(ragas_metrics, class_name, None)

                if metric_class is None:
                    metric_class = getattr(metric_collections, class_name, None)

                if metric_class is not None:
                    return metric_class

            raise ExternalServiceError(
                "ragas", f"ragas metric class not available: {class_names}"
            )

        metric_builders = {
            "context_precision": _resolve_metric_class("ContextPrecision"),
            "context_utilization": _resolve_metric_class("ContextUtilization"),
            "non_llm_context_precision": _resolve_metric_class(
                "NonLLMContextPrecisionWithReference"
            ),
            "id_based_context_precision": _resolve_metric_class(
                "IDBasedContextPrecision"
            ),
            "context_recall": _resolve_metric_class("ContextRecall"),
            "non_llm_context_recall": _resolve_metric_class("NonLLMContextRecall"),
            "id_based_context_recall": _resolve_metric_class("IDBasedContextRecall"),
            "context_entity_recall": _resolve_metric_class("ContextEntityRecall"),
            "answer_relevancy": _resolve_metric_class("AnswerRelevancy"),
            "faithfulness": _resolve_metric_class("Faithfulness"),
            "noise_sensitivity": _resolve_metric_class("NoiseSensitivity"),
            "topic_adherence": _resolve_metric_class("TopicAdherence"),
            "tool_call_accuracy": _resolve_metric_class("ToolCallAccuracy"),
            "tool_call_f1": _resolve_metric_class("ToolCallF1"),
            "agent_goal_accuracy": _resolve_metric_class("AgentGoalAccuracy"),
        }

        sample = SingleTurnSample(
            user_input=user_input,
            response=response,
            reference=reference or "",
            retrieved_contexts=retrieved_contexts,
            reference_contexts=reference_contexts or [],
            retrieved_context_ids=retrieved_context_ids or [],
            reference_context_ids=reference_context_ids or [],
        )

        sample_dict = sample.to_dict()
        dataset = Dataset.from_list([sample_dict])

        configured_requirements = self._load_metric_requirements_config()
        metrics = []

        for metric_name in metric_names:
            metric_builder = metric_builders[metric_name]

            required_args = configured_requirements.get(
                metric_name,
                self._infer_constructor_args_from_signature(metric_builder),
            )

            constructor_kwargs: dict[str, Any] = {}

            if "llm" in required_args:
                if llm is None:
                    raise ValueError(
                        f"Metric '{metric_name}' requires constructor argument: llm"
                    )
                constructor_kwargs["llm"] = llm

            if "embeddings" in required_args:
                if embeddings is None:
                    raise ValueError(
                        f"Metric '{metric_name}' requires constructor argument: embeddings"
                    )
                constructor_kwargs["embeddings"] = embeddings

            metric = (
                metric_builder(**constructor_kwargs)
                if isinstance(metric_builder, type)
                else metric_builder
            )

            if not isinstance(metric, Metric):
                raise ExternalServiceError(
                    "ragas",
                    (
                        f"Metric '{metric_name}' resolved to invalid object "
                        f"{type(metric)!r}. aevaluate requires initialized "
                        "ragas.metrics.base.Metric objects."
                    ),
                )

            metrics.append(metric)

        result = await aevaluate(
            dataset=dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=True,
            show_progress=False,
        )

        row = result.to_pandas().iloc[0].to_dict()

        return {
            metric_name: float(row[metric_name])
            for metric_name in metric_names
            if metric_name in row and row[metric_name] is not None
        }
