"""Workflow node registry."""

from app.core.config.logging import get_logger
from app.domain.workflows.nodes.base import WorkflowNode
from app.domain.workflows.nodes.chunking import (
    MarkdownHeaderSplitterNode,
    RecursiveTextSplitterNode,
)
from app.domain.workflows.nodes.embedding import (
    OllamaEmbeddingNode,
    OpenAIEmbeddingNode,
)
from app.domain.workflows.nodes.evaluation import RagasEvalNode
from app.domain.workflows.nodes.generation import LLMGenerationNode
from app.domain.workflows.nodes.guardrails import (
    InputGuardrailNode,
    OutputGuardrailNode,
)
from app.domain.workflows.nodes.reranking import CrossEncoderRerankerNode
from app.domain.workflows.nodes.retrieval import (
    HybridRetrievalNode,
    VectorRetrievalNode,
)

logger = get_logger(__name__)


class NodeRegistry:
    """Registry for workflow node implementations."""

    def __init__(self):
        self._nodes: dict[str, WorkflowNode] = {}

    def register(self, name: str, node: WorkflowNode) -> None:
        """Register a node implementation.

        Args:
            name: Unique node identifier
            node: Node implementation
        """
        self._nodes[name] = node
        logger.debug("node_registered name=%s", name)

    def get(self, name: str) -> WorkflowNode | None:
        """Get node implementation by name.

        Args:
            name: Node identifier

        Returns:
            Node implementation or None if not found
        """
        return self._nodes.get(name)

    def has(self, name: str) -> bool:
        """Check if node is registered.

        Args:
            name: Node identifier

        Returns:
            True if node is registered
        """
        return name in self._nodes

    def list_nodes(self) -> list[str]:
        """List all registered node names."""
        return list(self._nodes.keys())

    def get_node_types(self) -> dict[str, list[str]]:
        """Get nodes grouped by type category."""
        categories: dict[str, list[str]] = {}

        for name in self._nodes:
            # Infer category from node name
            if "chunk" in name.lower():
                category = "chunking"
            elif "embed" in name.lower():
                category = "embedding"
            elif "retriev" in name.lower():
                category = "retrieval"
            elif "rerank" in name.lower():
                category = "reranking"
            elif "generat" in name.lower() or "llm" in name.lower():
                category = "generation"
            elif "eval" in name.lower():
                category = "evaluation"
            elif "guard" in name.lower():
                category = "guardrails"
            else:
                category = "other"

            if category not in categories:
                categories[category] = []
            categories[category].append(name)

        return categories


# Create global registry
NODE_REGISTRY = NodeRegistry()

# Register default nodes
NODE_REGISTRY.register("recursive_text_splitter", RecursiveTextSplitterNode())
NODE_REGISTRY.register("markdown_header_splitter", MarkdownHeaderSplitterNode())
NODE_REGISTRY.register("openai_embedding", OpenAIEmbeddingNode())
NODE_REGISTRY.register("ollama_embedding", OllamaEmbeddingNode())
NODE_REGISTRY.register("vector_retrieval", VectorRetrievalNode())
NODE_REGISTRY.register("hybrid_retrieval", HybridRetrievalNode())
NODE_REGISTRY.register("cross_encoder_reranker", CrossEncoderRerankerNode())
NODE_REGISTRY.register("llm_generation", LLMGenerationNode())
NODE_REGISTRY.register("ragas_eval", RagasEvalNode())
NODE_REGISTRY.register("input_guardrail", InputGuardrailNode())
NODE_REGISTRY.register("output_guardrail", OutputGuardrailNode())


def get_registry() -> NodeRegistry:
    """Get the global node registry."""
    return NODE_REGISTRY
