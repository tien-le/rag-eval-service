"""LLM generation node implementations."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import NodeExecutionError, WorkflowNode

logger = get_logger(__name__)


class LLMGenerationNode(WorkflowNode):
    """LLM-based text generation."""

    def __init__(self):
        self.default_config = {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000,
            "system_prompt": "You are a helpful assistant.",
        }

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate text using LLM."""
        merged_config = {**self.default_config, **config}

        # Build prompt from input and retrieved context
        query = input_data.get("query", input_data.get("question", ""))
        context_docs = input_data.get("results", input_data.get("context", []))

        # Format context
        if context_docs:
            context_text = "\n\n".join(
                f"Document {i+1}: {doc.get('content', str(doc))}"
                for i, doc in enumerate(context_docs[:5])
            )
            prompt = f"Context:\n{context_text}\n\nQuestion: {query}\n\nAnswer:"
        else:
            prompt = query

        logger.debug(
            "llm_generation model=%s temperature=%.2f max_tokens=%d",
            merged_config["model"],
            merged_config["temperature"],
            merged_config["max_tokens"],
        )

        # TODO: Call LLM through gateway
        # Mock response
        mock_answer = f"Based on the context provided, I can answer: {query[:50]}..."

        return {
            "answer": mock_answer,
            "prompt": prompt,
            "model": merged_config["model"],
            "temperature": merged_config["temperature"],
            "max_tokens": merged_config["max_tokens"],
            "finish_reason": "stop",
        }

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate generation configuration."""
        errors = []

        temp = config.get("temperature", self.default_config["temperature"])
        if not (0 <= temp <= 2):
            errors.append("temperature must be between 0 and 2")

        max_tokens = config.get("max_tokens", self.default_config["max_tokens"])
        if not (1 <= max_tokens <= 32000):
            errors.append("max_tokens must be between 1 and 32000")

        return errors


# Node registry entry
GenerationNode = LLMGenerationNode
