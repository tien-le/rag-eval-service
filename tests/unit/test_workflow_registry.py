"""Tests for workflow node registry."""

import pytest

from app.domain.workflows.nodes.base import WorkflowNode
from app.domain.workflows.nodes.chunking import RecursiveTextSplitterNode
from app.domain.workflows.nodes.embedding import OpenAIEmbeddingNode
from app.domain.workflows.registry import NodeRegistry, get_registry


class TestNodeRegistry:
    """Test NodeRegistry functionality."""

    def test_register_and_get_node(self) -> None:
        """Test registering and retrieving a node."""
        registry = NodeRegistry()
        node = RecursiveTextSplitterNode()

        registry.register("test_chunker", node)
        retrieved = registry.get("test_chunker")

        assert retrieved is node

    def test_get_missing_node_returns_none(self) -> None:
        """Test that missing node returns None."""
        registry = NodeRegistry()

        result = registry.get("missing")
        assert result is None

    def test_has_node(self) -> None:
        """Test checking if node is registered."""
        registry = NodeRegistry()
        node = RecursiveTextSplitterNode()

        registry.register("test", node)

        assert registry.has("test") is True
        assert registry.has("missing") is False

    def test_list_nodes(self) -> None:
        """Test listing registered nodes."""
        registry = NodeRegistry()
        registry.register("a", RecursiveTextSplitterNode())
        registry.register("b", OpenAIEmbeddingNode())

        nodes = registry.list_nodes()

        assert "a" in nodes
        assert "b" in nodes
        assert len(nodes) == 2

    def test_get_node_types(self) -> None:
        """Test getting nodes grouped by type."""
        registry = NodeRegistry()
        registry.register("chunker", RecursiveTextSplitterNode())
        registry.register("embedder", OpenAIEmbeddingNode())
        registry.register("llm", OpenAIEmbeddingNode())

        types = registry.get_node_types()

        assert "chunking" in types
        assert "embedding" in types

    def test_register_overwrites_existing(self) -> None:
        """Test that register overwrites existing node."""
        registry = NodeRegistry()
        node1 = RecursiveTextSplitterNode()
        node2 = OpenAIEmbeddingNode()

        registry.register("test", node1)
        registry.register("test", node2)

        assert registry.get("test") is node2


class TestGlobalRegistry:
    """Test global node registry."""

    def test_global_registry_exists(self) -> None:
        """Test that global registry is populated."""
        registry = get_registry()

        # Check that default nodes are registered
        assert registry.has("recursive_text_splitter")
        assert registry.has("openai_embedding")
        assert registry.has("vector_retrieval")
        assert registry.has("llm_generation")
        assert registry.has("ragas_eval")

    def test_get_registered_nodes(self) -> None:
        """Test retrieving nodes from global registry."""
        registry = get_registry()

        chunker = registry.get("recursive_text_splitter")
        assert isinstance(chunker, RecursiveTextSplitterNode)

        embedder = registry.get("openai_embedding")
        assert isinstance(embedder, OpenAIEmbeddingNode)

    def test_all_registered_are_workflow_nodes(self) -> None:
        """Test that all registered nodes implement WorkflowNode protocol."""
        registry = get_registry()

        for name in registry.list_nodes():
            node = registry.get(name)
            assert isinstance(node, WorkflowNode), f"{name} is not a WorkflowNode"
