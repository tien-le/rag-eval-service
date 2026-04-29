"""Tests for workflow schemas."""

import pytest
from pydantic import ValidationError

from app.domain.workflows.schemas import (
    NodeType,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowStep,
)


class TestWorkflowStep:
    """Test WorkflowStep schema."""

    def test_create_step(self) -> None:
        """Test creating a workflow step."""
        step = WorkflowStep(
            id="chunk",
            type=NodeType.CHUNKING,
            implementation="recursive_text_splitter",
        )

        assert step.id == "chunk"
        assert step.type == NodeType.CHUNKING
        assert step.implementation == "recursive_text_splitter"
        assert step.config_override == {}

    def test_step_with_config(self) -> None:
        """Test step with configuration override."""
        step = WorkflowStep(
            id="embed",
            type=NodeType.EMBEDDING,
            implementation="openai_embedding",
            config_ref="embedding.default",
            config_override={"model": "text-embedding-3-large"},
        )

        assert step.config_ref == "embedding.default"
        assert step.config_override["model"] == "text-embedding-3-large"


class TestWorkflowEdge:
    """Test WorkflowEdge schema."""

    def test_create_edge(self) -> None:
        """Test creating a workflow edge."""
        edge = WorkflowEdge(
            **{"from": "chunk", "to": "embed"}  # Using alias
        )

        assert edge.from_step == "chunk"
        assert edge.to_step == "embed"
        assert edge.priority == 0

    def test_edge_with_condition(self) -> None:
        """Test edge with condition."""
        edge = WorkflowEdge(
            **{
                "from": "guard",
                "to": "process",
                "condition": "input.valid == true",
                "priority": 1,
            }
        )

        assert edge.condition == "input.valid == true"
        assert edge.priority == 1


class TestWorkflowDefinition:
    """Test WorkflowDefinition schema."""

    def test_create_minimal_workflow(self) -> None:
        """Test creating a minimal valid workflow."""
        workflow = WorkflowDefinition(
            id="test_workflow",
            steps=[
                WorkflowStep(
                    id="step1",
                    type=NodeType.GENERATION,
                    implementation="llm_generation",
                )
            ],
        )

        assert workflow.id == "test_workflow"
        assert workflow.version == 1
        assert len(workflow.steps) == 1

    def test_workflow_requires_steps(self) -> None:
        """Test that workflow requires at least one step."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowDefinition(
                id="test_workflow",
                steps=[],
            )

        assert "at least one step" in str(exc_info.value)

    def test_get_step_by_id(self) -> None:
        """Test getting step by ID."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(id="a", type=NodeType.CHUNKING, implementation="splitter"),
                WorkflowStep(id="b", type=NodeType.EMBEDDING, implementation="embedder"),
            ],
        )

        step = workflow.get_step("a")
        assert step is not None
        assert step.id == "a"

        missing = workflow.get_step("c")
        assert missing is None

    def test_get_step_order_linear(self) -> None:
        """Test getting execution order for linear workflow."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(id="a", type=NodeType.CHUNKING, implementation="splitter"),
                WorkflowStep(id="b", type=NodeType.EMBEDDING, implementation="embedder"),
                WorkflowStep(id="c", type=NodeType.RETRIEVAL, implementation="retriever"),
            ],
            edges=[
                WorkflowEdge(**{"from": "a", "to": "b"}),
                WorkflowEdge(**{"from": "b", "to": "c"}),
            ],
        )

        order = workflow.get_step_order()
        assert order == ["a", "b", "c"]

    def test_get_step_order_detects_cycle(self) -> None:
        """Test that cycle detection raises error."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(id="a", type=NodeType.CHUNKING, implementation="splitter"),
                WorkflowStep(id="b", type=NodeType.EMBEDDING, implementation="embedder"),
            ],
            edges=[
                WorkflowEdge(**{"from": "a", "to": "b"}),
                WorkflowEdge(**{"from": "b", "to": "a"}),
            ],
        )

        with pytest.raises(ValueError, match="cycles"):
            workflow.get_step_order()

    def test_compute_hash_consistency(self) -> None:
        """Test that hash is consistent for same definition."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(id="a", type=NodeType.GENERATION, implementation="llm"),
            ],
        )

        hash1 = workflow.compute_hash()
        hash2 = workflow.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 32  # Hex digest of first 16 bytes

    def test_compute_hash_changes_with_definition(self) -> None:
        """Test that hash changes when definition changes."""
        workflow1 = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(id="a", type=NodeType.GENERATION, implementation="llm"),
            ],
        )

        workflow2 = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(id="a", type=NodeType.GENERATION, implementation="different"),
            ],
        )

        hash1 = workflow1.compute_hash()
        hash2 = workflow2.compute_hash()

        assert hash1 != hash2

    def test_edge_validation(self) -> None:
        """Test edge validation with unknown steps."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowDefinition(
                id="test",
                steps=[
                    WorkflowStep(id="a", type=NodeType.GENERATION, implementation="llm"),
                ],
                edges=[
                    WorkflowEdge(**{"from": "a", "to": "unknown"}),
                ],
            )

        assert "unknown step" in str(exc_info.value).lower()
