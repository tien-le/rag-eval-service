"""Base workflow node interface."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkflowNode(Protocol):
    """Protocol for all workflow nodes.

    Every node must implement this interface to be registered
    in the workflow registry.
    """

    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the node.

        Args:
            input_data: Input data from previous step or workflow input
            config: Resolved configuration for this node
            context: Execution context (tenant_id, trace_id, etc.)

        Returns:
            Output data for next step or workflow output

        Raises:
            NodeExecutionError: If node execution fails
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Validate node configuration.

        Args:
            config: Configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        return []


class NodeContext:
    """Context passed to node execution."""

    def __init__(
        self,
        tenant_id: str,
        trace_id: str,
        workflow_id: str | None = None,
        step_id: str | None = None,
        parent_context: dict[str, Any] | None = None,
    ):
        self.tenant_id = tenant_id
        self.trace_id = trace_id
        self.workflow_id = workflow_id
        self.step_id = step_id
        self.parent_context = parent_context or {}
        self.metadata: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context."""
        if key in self.metadata:
            return self.metadata[key]
        return self.parent_context.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in context."""
        self.metadata[key] = value


class NodeExecutionError(Exception):
    """Raised when node execution fails."""

    def __init__(
        self,
        node_type: str,
        node_id: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.node_type = node_type
        self.node_id = node_id
        self.details = details or {}
        super().__init__(f"Node {node_id} ({node_type}): {message}")


class NodeValidationError(Exception):
    """Raised when node validation fails."""

    def __init__(self, node_type: str, errors: list[str]):
        self.node_type = node_type
        self.errors = errors
        super().__init__(f"Validation failed for {node_type}: {'; '.join(errors)}")
