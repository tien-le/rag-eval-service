"""Evaluation node implementations."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import WorkflowNode

logger = get_logger(__name__)


class RagasEvalNode(WorkflowNode):
    """RAG evaluation using Ragas metrics."""

    def __init__(self):
        self.default_config = {
            "metrics": ["faithfulness", "answer_relevancy"],
            "llm_model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-small",
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate RAG quality using Ragas."""
        merged_config = {**self.default_config, **config}

        question = input_data.get("question", input_data.get("query", ""))
        answer = input_data.get("answer", input_data.get("generation", ""))
        contexts = input_data.get("contexts") or input_data.get("results", [])
        ground_truth = input_data.get("ground_truth")

        metrics = merged_config["metrics"]

        logger.debug(
            "ragas_evaluation metrics=%s question_len=%d",
            metrics,
            len(question),
        )

        # TODO: Call Ragas through evaluation service
        # Mock scores
        scores = {}
        for metric in metrics:
            # Generate realistic mock scores
            import random

            random.seed(hash(question + metric) % 10000)
            scores[metric] = round(random.uniform(0.6, 0.95), 2)

        result = {
            "scores": scores,
            "metrics": metrics,
            "overall_score": round(sum(scores.values()) / len(scores), 2) if scores else 0,
            "passed": all(s >= 0.7 for s in scores.values()),
        }

        if ground_truth:
            # Calculate additional comparison metrics
            result["ground_truth_comparison"] = {
                "answer_similarity": round(random.uniform(0.6, 0.95), 2),
            }

        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate evaluation configuration."""
        errors = []

        valid_metrics = [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "context_relevance",
            "hallucination",
        ]

        metrics = config.get("metrics", self.default_config["metrics"])
        invalid = [m for m in metrics if m not in valid_metrics]
        if invalid:
            errors.append(f"Invalid metrics: {invalid}. Valid: {valid_metrics}")

        return errors


# Node registry entry
EvaluationNode = RagasEvalNode
