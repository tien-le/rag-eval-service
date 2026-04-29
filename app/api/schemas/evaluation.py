"""Pydantic schemas for evaluation APIs."""

from pydantic import BaseModel, Field


class ClassificationMetricsRequest(BaseModel):
    actual: list[str] = Field(min_length=1)
    predicted: list[str] = Field(min_length=1)
    positive_label: str = Field(default="positive")


class ClassificationMetricsResponse(BaseModel):
    summary: dict
    actual_distribution: dict[str, int]
    predicted_distribution: dict[str, int]


class RagasSingleTurnRequest(BaseModel):
    user_input: str
    response: str
    retrieved_contexts: list[str] = Field(min_length=1)
    reference_contexts: list[str] | None = None
    retrieved_context_ids: list[str] | None = None
    reference_context_ids: list[str] | None = None
    reference: str | None = None
    metric_names: list[str] = Field(min_length=1)


class RagasSingleTurnResponse(BaseModel):
    scores: dict[str, float]


class MetricCatalogResponse(BaseModel):
    metrics: list[dict]

