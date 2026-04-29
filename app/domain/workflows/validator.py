"""Workflow validation logic."""

from typing import Any

from app.core.config.logging import get_logger
from app.domain.workflows.registry import get_registry
from app.domain.workflows.schemas import WorkflowDefinition

logger = get_logger(__name__)


class WorkflowValidationError(Exception):
    """Raised when workflow validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Workflow validation failed: {'; '.join(errors)}")


class WorkflowValidator:
    """Validator for workflow definitions."""

    def validate(self, workflow: WorkflowDefinition | dict[str, Any]) -> list[str]:
        """Validate workflow definition.

        Args:
            workflow: Workflow definition to validate

        Returns:
            List of validation errors (empty if valid)
        """
        if isinstance(workflow, dict):
            workflow = WorkflowDefinition.model_validate(workflow)

        errors: list[str] = []

        # Validate steps
        errors.extend(self._validate_steps(workflow))

        # Validate edges
        errors.extend(self._validate_edges(workflow))

        # Validate connectivity
        errors.extend(self._validate_connectivity(workflow))

        return errors

    def validate_strict(self, workflow: WorkflowDefinition | dict[str, Any]) -> None:
        """Validate workflow and raise on errors.

        Args:
            workflow: Workflow definition to validate

        Raises:
            WorkflowValidationError: If validation fails
        """
        errors = self.validate(workflow)
        if errors:
            raise WorkflowValidationError(errors)

    def _validate_steps(self, workflow: WorkflowDefinition) -> list[str]:
        """Validate workflow steps."""
        errors: list[str] = []
        registry = get_registry()

        step_ids: set[str] = set()

        for step in workflow.steps:
            # Check for duplicate IDs
            if step.id in step_ids:
                errors.append(f"Duplicate step ID: {step.id}")
            step_ids.add(step.id)

            # Check node is registered
            if not registry.has(step.implementation):
                errors.append(
                    f"Step '{step.id}': Unknown implementation '{step.implementation}'"
                )

            # Validate config if node exists
            node = registry.get(step.implementation)
            if node and step.config_override:
                config_errors = node.validate_config(step.config_override)
                for err in config_errors:
                    errors.append(f"Step '{step.id}': {err}")

        return errors

    def _validate_edges(self, workflow: WorkflowDefinition) -> list[str]:
        """Validate workflow edges."""
        errors: list[str] = []
        step_ids = {step.id for step in workflow.steps}

        for i, edge in enumerate(workflow.edges):
            # Check source exists
            if edge.from_step not in step_ids:
                errors.append(f"Edge {i}: Source step '{edge.from_step}' not found")

            # Check target exists
            if edge.to_step not in step_ids:
                errors.append(f"Edge {i}: Target step '{edge.to_step}' not found")

            # Check for self-loops
            if edge.from_step == edge.to_step:
                errors.append(f"Edge {i}: Self-loops are not allowed ({edge.from_step})")

        return errors

    def _validate_connectivity(self, workflow: WorkflowDefinition) -> list[str]:
        """Validate workflow is connected and has no cycles."""
        errors: list[str] = []

        if not workflow.steps:
            return errors

        step_ids = {step.id for step in workflow.steps}

        # Find unreachable steps
        if workflow.edges:
            reachable = self._get_reachable_steps(workflow)
            unreachable = step_ids - reachable

            if unreachable:
                errors.append(f"Unreachable steps: {', '.join(unreachable)}")

        # Check for cycles using topological sort
        try:
            workflow.get_step_order()
        except ValueError as e:
            errors.append(str(e))

        return errors

    def _get_reachable_steps(self, workflow: WorkflowDefinition) -> set[str]:
        """Get all steps reachable from the first step."""
        if not workflow.steps:
            return set()

        # Build adjacency list
        graph: dict[str, list[str]] = {step.id: [] for step in workflow.steps}
        for edge in workflow.edges:
            if edge.from_step in graph:
                graph[edge.from_step].append(edge.to_step)

        # BFS from first step
        start = workflow.steps[0].id
        reachable: set[str] = set()
        queue = [start]

        while queue:
            current = queue.pop(0)
            if current not in reachable:
                reachable.add(current)
                queue.extend(graph.get(current, []))

        return reachable


# Singleton instance
_validator: WorkflowValidator | None = None


def get_validator() -> WorkflowValidator:
    """Get validator singleton."""
    global _validator
    if _validator is None:
        _validator = WorkflowValidator()
    return _validator
