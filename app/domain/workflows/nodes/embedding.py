"""Embedding node implementations."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import NodeExecutionError, WorkflowNode

logger = get_logger(__name__)


class OpenAIEmbeddingNode(WorkflowNode):
    """Generate embeddings using OpenAI API."""

    def __init__(self):
        self.default_config = {
            "model": "text-embedding-3-small",
            "dimensions": 1536,
            "batch_size": 100,
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate embeddings for input text."""
        merged_config = {**self.default_config, **config}

        # Get input texts
        texts = input_data.get("texts") or input_data.get("chunks", [])
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return {"embeddings": [], "dimensions": merged_config["dimensions"]}

        # TODO: Call OpenAI API through LLM gateway
        # For now, return mock embeddings
        dimensions = merged_config["dimensions"]
        mock_embeddings = [[0.0] * dimensions for _ in texts]

        logger.debug(
            "embeddings_generated count=%d model=%s",
            len(texts),
            merged_config["model"],
        )

        return {
            "embeddings": mock_embeddings,
            "dimensions": dimensions,
            "model": merged_config["model"],
            "count": len(texts),
        }

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate embedding configuration."""
        errors = []

        valid_models = ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]
        model = config.get("model", self.default_config["model"])
        if model not in valid_models:
            errors.append(f"model must be one of {valid_models}")

        dimensions = config.get("dimensions", 1536)
        if not (256 <= dimensions <= 3072):
            errors.append("dimensions must be between 256 and 3072")

        return errors


class OllamaEmbeddingNode(WorkflowNode):
    """Generate embeddings using local Ollama."""

    def __init__(self):
        self.default_config = {
            "model": "nomic-embed-text",
            "base_url": "http://localhost:11434",
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate embeddings using Ollama."""
        merged_config = {**self.default_config, **config}

        texts = input_data.get("texts") or input_data.get("chunks", [])
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return {"embeddings": [], "model": merged_config["model"]}

        # TODO: Call Ollama API
        logger.debug(
            "ollama_embeddings count=%d model=%s",
            len(texts),
            merged_config["model"],
        )

        # Return mock embeddings
        return {
            "embeddings": [[0.0] * 768 for _ in texts],
            "model": merged_config["model"],
            "count": len(texts),
        }


# Node registry entry
EmbeddingNode = OpenAIEmbeddingNode
