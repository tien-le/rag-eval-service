"""Workflow domain service."""

from typing import Any
from uuid import UUID

from app.core.config.logging import get_logger
from app.domain.workflows.schemas import WorkflowDefinition, WorkflowVersion
from app.domain.workflows.validator import WorkflowValidator, WorkflowValidationError

logger = get_logger(__name__)


class WorkflowService:
    """Service for workflow management operations."""

    def __init__(self, validator: WorkflowValidator | None = None):
        self.validator = validator or WorkflowValidator()

    async def create_workflow(
        self,
        definition: dict[str, Any],
        tenant_id: str,
        created_by: str | None = None,
    ) -> WorkflowVersion:
        """Create new workflow version.

        Args:
            definition: Workflow definition
            tenant_id: Tenant identifier
            created_by: Creator user ID

        Returns:
            Created workflow version

        Raises:
            WorkflowValidationError: If definition is invalid
        """
        # Validate definition
        workflow_def = WorkflowDefinition.model_validate(definition)
        self.validator.validate_strict(workflow_def)

        # Compute hash
        definition_hash = workflow_def.compute_hash()

        # Create version
        version = WorkflowVersion(
            workflow_id=UUID(int=0),  # Will be set by repository
            version=1,
            definition=workflow_def,
            definition_hash=definition_hash,
            created_by=created_by,
            status="draft",
        )

        logger.info(
            "workflow_created tenant=%s workflow_id=%s version=%d",
            tenant_id,
            workflow_def.id,
            version.version,
        )

        return version

    async def validate_workflow(
        self,
        definition: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate workflow definition without saving.

        Args:
            definition: Workflow definition to validate

        Returns:
            Validation result with errors if any
        """
        try:
            workflow_def = WorkflowDefinition.model_validate(definition)
            errors = self.validator.validate(workflow_def)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "step_count": len(workflow_def.steps),
                "edge_count": len(workflow_def.edges),
                "definition_hash": workflow_def.compute_hash(),
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "step_count": 0,
                "edge_count": 0,
                "definition_hash": None,
            }

    async def publish_version(
        self,
        version_id: UUID,
        published_by: str | None = None,
    ) -> WorkflowVersion:
        """Publish a workflow version.

        Args:
            version_id: Version ID to publish
            published_by: User publishing the version

        Returns:
            Published workflow version
        """
        # TODO: Implement with repository
        from datetime import UTC, datetime

        logger.info(
            "workflow_published version_id=%s by=%s",
            version_id,
            published_by,
        )

        # Placeholder return
        raise NotImplementedError("Repository required for publish operation")

    async def get_workflow_dry_run_result(
        self,
        definition: dict[str, Any],
        test_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Run workflow in dry-run mode.

        Args:
            definition: Workflow definition
            test_input: Test input data

        Returns:
            Dry-run result
        """
        # Validate first
        validation = await self.validate_workflow(definition)
        if not validation["valid"]:
            return {
                "success": False,
                "validation_errors": validation["errors"],
            }

        # TODO: Implement dry-run execution
        logger.info("workflow_dry_run workflow_id=%s", definition.get("id"))

        return {
            "success": True,
            "validation_errors": [],
            "estimated_steps": validation["step_count"],
            "mock_output": {"dry_run": True},
        }


# Singleton instance
_service: WorkflowService | None = None


def get_workflow_service() -> WorkflowService:
    """Get workflow service singleton."""
    global _service
    if _service is None:
        _service = WorkflowService()
    return _service
