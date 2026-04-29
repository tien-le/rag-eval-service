"""Reranking node implementations."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import WorkflowNode

logger = get_logger(__name__)


class CrossEncoderRerankerNode(WorkflowNode):
    """Rerank retrieval results using cross-encoder."""

    def __init__(self):
        self.default_config = {
            "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "top_k": 5,
            "batch_size": 32,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Rerank documents using cross-encoder model."""
        merged_config = {**self.default_config, **config}

        query = input_data.get("query", "")
        documents = input_data.get("results") or input_data.get("documents", [])

        if not documents:
            return {"results": [], "query": query}

        top_k = min(merged_config["top_k"], len(documents))

        # TODO: Call cross-encoder model for reranking
        logger.debug(
            "reranking documents=%d top_k=%d model=%s",
            len(documents),
            top_k,
            merged_config["model"],
        )

        # Mock reranking - re-sort by a mock score
        reranked = sorted(
            documents,
            key=lambda x: x.get("score", 0) * 1.1,  # Boost original scores
            reverse=True,
        )[:top_k]

        # Add rerank score
        for i, doc in enumerate(reranked):
            doc["rerank_score"] = 0.95 - (i * 0.02)
            doc["rerank_position"] = i + 1

        return {
            "results": reranked,
            "count": len(reranked),
            "query": query,
            "model": merged_config["model"],
        }

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate reranker configuration."""
        errors = []

        top_k = config.get("top_k", self.default_config["top_k"])
        if not (1 <= top_k <= 100):
            errors.append("top_k must be between 1 and 100")

        return errors


# Node registry entry
RerankingNode = CrossEncoderRerankerNode
