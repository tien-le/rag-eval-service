"""Tests for workflow validator."""

import pytest

from app.domain.workflows.schemas import (
    NodeType,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowStep,
)
from app.domain.workflows.validator import WorkflowValidationError, WorkflowValidator


class TestWorkflowValidator:
    """Test WorkflowValidator functionality."""

    @pytest.fixture
    def validator(self) -> WorkflowValidator:
        """Create validator instance."""
        return WorkflowValidator()

    def test_valid_workflow_no_errors(self, validator: WorkflowValidator) -> None:
        """Test that valid workflow returns no errors."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="step1",
                    type=NodeType.GENERATION,
                    implementation="llm_generation",
                ),
            ],
        )

        errors = validator.validate(workflow)
        assert errors == []

    def test_detect_duplicate_step_ids(self, validator: WorkflowValidator) -> None:
        """Test detection of duplicate step IDs."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="step1",
                    type=NodeType.GENERATION,
                    implementation="llm_generation",
                ),
                WorkflowStep(
                    id="step1",
                    type=NodeType.CHUNKING,
                    implementation="recursive_text_splitter",
                ),
            ],
        )

        errors = validator.validate(workflow)

        assert any("duplicate" in e.lower() for e in errors)

    def test_detect_unknown_implementation(self, validator: WorkflowValidator) -> None:
        """Test detection of unknown node implementation."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="step1", type=NodeType.GENERATION, implementation="unknown_node"
                ),
            ],
        )

        errors = validator.validate(workflow)

        assert any("unknown implementation" in e.lower() for e in errors)

    def test_detect_invalid_edge_source(self, validator: WorkflowValidator) -> None:
        """Test detection of edge with invalid source (pydantic catches first)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            WorkflowDefinition(
                id="test",
                steps=[
                    WorkflowStep(
                        id="step1",
                        type=NodeType.GENERATION,
                        implementation="llm_generation",
                    ),
                ],
                edges=[
                    WorkflowEdge(**{"from": "missing", "to": "step1"}),
                ],
            )

        assert "unknown step" in str(exc_info.value).lower()

    def test_detect_self_loop(self, validator: WorkflowValidator) -> None:
        """Test detection of self-loop edges."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="step1",
                    type=NodeType.GENERATION,
                    implementation="llm_generation",
                ),
            ],
            edges=[
                WorkflowEdge(**{"from": "step1", "to": "step1"}),
            ],
        )

        errors = validator.validate(workflow)

        assert any("self-loop" in e.lower() for e in errors)

    def test_detect_cycle(self, validator: WorkflowValidator) -> None:
        """Test detection of cyclic workflow."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="a", type=NodeType.GENERATION, implementation="llm_generation"
                ),
                WorkflowStep(
                    id="b",
                    type=NodeType.CHUNKING,
                    implementation="recursive_text_splitter",
                ),
            ],
            edges=[
                WorkflowEdge(**{"from": "a", "to": "b"}),
                WorkflowEdge(**{"from": "b", "to": "a"}),
            ],
        )

        errors = validator.validate(workflow)

        assert any("cycle" in e.lower() for e in errors)

    def test_detect_unreachable_steps(self, validator: WorkflowValidator) -> None:
        """Test detection of unreachable steps."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="a", type=NodeType.GENERATION, implementation="llm_generation"
                ),
                WorkflowStep(
                    id="b",
                    type=NodeType.CHUNKING,
                    implementation="recursive_text_splitter",
                ),
                WorkflowStep(
                    id="c", type=NodeType.EMBEDDING, implementation="openai_embedding"
                ),
            ],
            edges=[
                WorkflowEdge(**{"from": "a", "to": "b"}),
            ],
        )

        errors = validator.validate(workflow)

        assert any("unreachable" in e.lower() for e in errors)
        assert any("c" in e for e in errors)

    def test_validate_strict_raises_on_errors(
        self, validator: WorkflowValidator
    ) -> None:
        """Test that validate_strict raises on errors."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="step1", type=NodeType.GENERATION, implementation="unknown"
                ),
            ],
        )

        with pytest.raises(WorkflowValidationError) as exc_info:
            validator.validate_strict(workflow)

        assert "validation failed" in str(exc_info.value).lower()

    def test_validate_strict_passes_on_valid(
        self, validator: WorkflowValidator
    ) -> None:
        """Test that validate_strict passes on valid workflow."""
        workflow = WorkflowDefinition(
            id="test",
            steps=[
                WorkflowStep(
                    id="step1",
                    type=NodeType.GENERATION,
                    implementation="llm_generation",
                ),
            ],
        )

        # Should not raise
        validator.validate_strict(workflow)

    def test_validate_from_dict(self, validator: WorkflowValidator) -> None:
        """Test validation from dictionary input."""
        definition = {
            "id": "test",
            "steps": [
                {
                    "id": "step1",
                    "type": "generation",
                    "implementation": "unknown_node",
                }
            ],
        }

        errors = validator.validate(definition)

        assert any("unknown implementation" in e.lower() for e in errors)
