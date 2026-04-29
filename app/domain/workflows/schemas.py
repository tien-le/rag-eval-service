"""Workflow definition schemas."""

from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    """Workflow node types."""

    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    RETRIEVAL = "retrieval"
    RERANKING = "reranking"
    GENERATION = "generation"
    EVALUATION = "evaluation"
    GUARDRAILS = "guardrails"
    TOOLS = "tools"
    MCP = "mcp"


class WorkflowStep(BaseModel):
    """A step in a workflow."""

    id: str = Field(description="Unique step identifier within workflow")
    type: NodeType = Field(description="Node type category")
    implementation: str = Field(description="Specific implementation to use")
    config_ref: str | None = Field(None, description="Reference to shared config")
    config_override: dict[str, Any] = Field(default_factory=dict, description="Step-specific config overrides")
    inputs: dict[str, str] | None = Field(None, description="Input mappings from previous steps")
    outputs: list[str] | None = Field(None, description="Output field names")
    condition: str | None = Field(None, description="Conditional execution expression")
    retry_policy: dict[str, Any] | None = Field(None, description="Retry configuration")


class WorkflowEdge(BaseModel):
    """Connection between workflow steps."""

    from_step: str = Field(alias="from", description="Source step ID")
    to_step: str = Field(alias="to", description="Target step ID")
    condition: str | None = Field(None, description="Edge condition expression")
    priority: int = Field(default=0, ge=0, le=100, description="Edge priority for conditional routing")

    model_config = {"populate_by_name": True}


class QualityGate(BaseModel):
    """Quality gate thresholds."""

    metric: str = Field(description="Metric name")
    threshold: float = Field(ge=0, le=1, description="Minimum acceptable score")
    operator: Literal["gte", "lte", "eq"] = "gte"


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    id: str = Field(description="Unique workflow identifier")
    version: int = Field(default=1, ge=1, description="Workflow version")
    name: str | None = Field(None, description="Human-readable name")
    description: str | None = Field(None, description="Workflow description")
    input_schema: str | None = Field(None, description="Input data schema reference")
    output_schema: str | None = Field(None, description="Output data schema reference")
    steps: list[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="Step connections")
    quality_gates: dict[str, float] = Field(default_factory=dict, description="Quality thresholds by metric")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tenant_id: str | None = Field(None, description="Owning tenant")
    created_by: str | None = Field(None, description="Creator identifier")

    @field_validator("steps")
    @classmethod
    def validate_steps_not_empty(cls, v: list[WorkflowStep]) -> list[WorkflowStep]:
        """Ensure workflow has at least one step."""
        if not v:
            raise ValueError("Workflow must have at least one step")
        return v

    @field_validator("edges")
    @classmethod
    def validate_edge_references(cls, v: list[WorkflowEdge], info) -> list[WorkflowEdge]:
        """Validate edge references exist in steps."""
        if not v:
            return v

        # Get step IDs from context if available
        steps = info.data.get("steps", [])
        step_ids = {step.id for step in steps}

        for edge in v:
            if edge.from_step not in step_ids:
                raise ValueError(f"Edge references unknown step: {edge.from_step}")
            if edge.to_step not in step_ids:
                raise ValueError(f"Edge references unknown step: {edge.to_step}")

        return v

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Get step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_step_order(self) -> list[str]:
        """Get step execution order using topological sort."""
        # Build adjacency list
        graph: dict[str, list[str]] = {step.id: [] for step in self.steps}
        in_degree: dict[str, int] = {step.id: 0 for step in self.steps}

        for edge in self.edges:
            graph[edge.from_step].append(edge.to_step)
            in_degree[edge.to_step] += 1

        # Kahn's algorithm
        queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
        order: list[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.steps):
            raise ValueError("Workflow contains cycles")

        return order

    def compute_hash(self) -> str:
        """Compute deterministic hash of workflow definition."""
        import hashlib
        import json

        # Create canonical representation
        canonical = self.model_dump(exclude={"metadata", "version"}, by_alias=True, mode="json")
        canonical_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))

        return hashlib.sha256(canonical_str.encode()).hexdigest()[:32]


class WorkflowVersion(BaseModel):
    """Workflow version record."""

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    version: int
    definition: WorkflowDefinition
    definition_hash: str
    status: Literal["draft", "published", "archived"] = "draft"
    created_by: str | None = None
    changelog: str | None = None
    published_at: str | None = None


class WorkflowRun(BaseModel):
    """Workflow execution record."""

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    workflow_version_id: UUID
    tenant_id: str
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None = None
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    trace_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
