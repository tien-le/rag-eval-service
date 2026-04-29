"""Retrieval node implementations."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import NodeExecutionError, WorkflowNode

logger = get_logger(__name__)


class VectorRetrievalNode(WorkflowNode):
    """Vector similarity retrieval from vector store."""

    def __init__(self):
        self.default_config = {
            "top_k": 5,
            "collection_name": "default",
            "filter": None,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Retrieve similar documents using vector search."""
        merged_config = {**self.default_config, **config}

        query_embedding = input_data.get("query_embedding") or input_data.get("embedding")
        if not query_embedding and "query" in input_data:
            # Need to embed query first (should be done in previous step)
            raise NodeExecutionError(
                node_type="retrieval",
                node_id=merged_config.get("step_id", "unknown"),
                message="Query embedding required. Add embedding step before retrieval.",
            )

        top_k = merged_config["top_k"]

        # TODO: Call vector store (Qdrant/Pinecone/Weaviate)
        logger.debug(
            "vector_retrieval top_k=%d collection=%s",
            top_k,
            merged_config["collection_name"],
        )

        # Return mock results
        mock_results = [
            {
                "id": f"doc_{i}",
                "content": f"Retrieved document {i}",
                "score": 0.95 - (i * 0.05),
                "metadata": {"source": "mock"},
            }
            for i in range(min(top_k, 5))
        ]

        return {
            "results": mock_results,
            "count": len(mock_results),
            "query_embedding": query_embedding,
        }

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate retrieval configuration."""
        errors = []

        top_k = config.get("top_k", self.default_config["top_k"])
        if not (1 <= top_k <= 100):
            errors.append("top_k must be between 1 and 100")

        return errors


class HybridRetrievalNode(WorkflowNode):
    """Hybrid retrieval combining vector and keyword search."""

    def __init__(self):
        self.default_config = {
            "vector_weight": 0.7,
            "keyword_weight": 0.3,
            "top_k": 5,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Hybrid retrieval using vector + keyword search."""
        merged_config = {**self.default_config, **config}

        query = input_data.get("query", "")
        query_embedding = input_data.get("query_embedding")

        logger.debug(
            "hybrid_retrieval top_k=%d vector_weight=%.2f",
            merged_config["top_k"],
            merged_config["vector_weight"],
        )

        # Mock hybrid results
        return {
            "results": [
                {
                    "id": f"hybrid_{i}",
                    "content": f"Hybrid result {i} for: {query[:50]}...",
                    "vector_score": 0.9 - (i * 0.05),
                    "keyword_score": 0.85 - (i * 0.05),
                    "combined_score": 0.88 - (i * 0.05),
                }
                for i in range(min(merged_config["top_k"], 5))
            ],
            "count": min(merged_config["top_k"], 5),
        }


# Node registry entry
RetrievalNode = VectorRetrievalNode
