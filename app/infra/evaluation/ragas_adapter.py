"""Ragas adapter for metric execution."""

import inspect
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config.exceptions import ExternalServiceError
from app.core.config.metric_catalog import METRIC_CATALOG


class LangChainEmbeddingsAdapter:
    """Adapter to make LangChain embeddings compatible with older Ragas versions.

    Ragas 0.4.x expects embed_query() method, but LangChain 1.x uses embed_text().
    This wrapper adds the legacy method for backward compatibility.
    """

    def __init__(self, embeddings: Any) -> None:
        self._embeddings = embeddings

    def embed_query(self, text: str) -> list[float]:
        """Legacy method for Ragas compatibility."""
        # Try embed_text first (LangChain 1.x), fallback to embed_query
        if hasattr(self._embeddings, "embed_text"):
            return self._embeddings.embed_text(text)
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Legacy method for Ragas compatibility."""
        if hasattr(self._embeddings, "embed_text"):
            return self._embeddings.embed_text(texts)
        return self._embeddings.embed_documents(texts)


class RagasAdapter:
    """Best-effort adapter around ragas imports and execution."""

    SUPPORTED_METRICS = {
        m.name
        for m in METRIC_CATALOG
        if m.category in {"retrieval", "generation", "robustness", "agent"}
    }
    # These metrics require MultiTurnSample or a different ascore API (conversation
    # messages + reference_topics) and cannot be evaluated via the single-turn endpoint.
    MULTI_TURN_ONLY_METRICS = frozenset(
        {
            "topic_adherence",
            "tool_call_accuracy",
            "tool_call_f1",
            "agent_goal_accuracy",
        }
    )
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

        multi_turn_requested = [
            m for m in metric_names if m in self.MULTI_TURN_ONLY_METRICS
        ]
        if multi_turn_requested:
            raise ValueError(
                f"Metrics {multi_turn_requested} require multi-turn conversation data "
                "and cannot be evaluated via the single-turn endpoint."
            )

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
                # Wrap embeddings to provide embed_query for Ragas 0.4.x compatibility
                constructor_kwargs["embeddings"] = LangChainEmbeddingsAdapter(
                    embeddings
                )

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
            embeddings=LangChainEmbeddingsAdapter(embeddings) if embeddings is not None else None,
            raise_exceptions=True,
            show_progress=False,
        )

        row = result.to_pandas().iloc[0].to_dict()

        return {
            metric_name: float(row[metric_name])
            for metric_name in metric_names
            if metric_name in row and row[metric_name] is not None
        }

    async def run_multi_turn(
        self,
        *,
        messages: list[dict[str, Any]],
        reference: str | None,
        reference_topics: list[str] | None,
        reference_tool_calls: list[dict[str, Any]] | None,
        metric_names: Sequence[str],
        llm: Any | None = None,
    ) -> dict[str, Any]:
        unsupported = [
            m for m in metric_names if m not in self.MULTI_TURN_ONLY_METRICS
        ]
        if unsupported:
            raise ValueError(
                f"Metrics {unsupported} are not supported by the multi-turn endpoint. "
                f"Supported: {sorted(self.MULTI_TURN_ONLY_METRICS)}"
            )

        try:
            from ragas.messages import AIMessage, HumanMessage, ToolCall, ToolMessage
            from ragas.metrics.collections import (
                AgentGoalAccuracyWithReference,
                ToolCallAccuracy,
                ToolCallF1,
                TopicAdherence,
            )
        except Exception as exc:
            raise ExternalServiceError(
                "ragas", f"ragas is not available: {exc}"
            ) from exc

        ragas_messages: list[Any] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            raw_tool_calls = msg.get("tool_calls") or []
            if role == "human":
                ragas_messages.append(HumanMessage(content=content))
            elif role == "ai":
                tc_list = (
                    [ToolCall(name=tc["name"], args=tc["args"]) for tc in raw_tool_calls]
                    if raw_tool_calls
                    else None
                )
                ragas_messages.append(AIMessage(content=content, tool_calls=tc_list))
            elif role == "tool":
                ragas_messages.append(ToolMessage(content=content))

        ref_tool_calls: list[Any] | None = None
        if reference_tool_calls is not None:
            ref_tool_calls = [
                ToolCall(name=tc["name"], args=tc["args"])
                for tc in reference_tool_calls
            ]

        scores: dict[str, Any] = {}

        for metric_name in metric_names:
            if metric_name == "topic_adherence":
                if not reference_topics:
                    raise ValueError("topic_adherence requires reference_topics")
                if llm is None:
                    raise ValueError("topic_adherence requires llm")
                result = await TopicAdherence(llm=llm).ascore(
                    user_input=ragas_messages,
                    reference_topics=reference_topics,
                )
            elif metric_name == "agent_goal_accuracy":
                if not reference:
                    raise ValueError("agent_goal_accuracy requires reference")
                if llm is None:
                    raise ValueError("agent_goal_accuracy requires llm")
                result = await AgentGoalAccuracyWithReference(llm=llm).ascore(
                    user_input=ragas_messages,
                    reference=reference,
                )
            elif metric_name == "tool_call_accuracy":
                if ref_tool_calls is None:
                    raise ValueError("tool_call_accuracy requires reference_tool_calls")
                result = await ToolCallAccuracy().ascore(
                    user_input=ragas_messages,
                    reference_tool_calls=ref_tool_calls,
                )
            elif metric_name == "tool_call_f1":
                if ref_tool_calls is None:
                    raise ValueError("tool_call_f1 requires reference_tool_calls")
                result = await ToolCallF1().ascore(
                    user_input=ragas_messages,
                    reference_tool_calls=ref_tool_calls,
                )

            scores[metric_name] = float(result.value)

        return scores
