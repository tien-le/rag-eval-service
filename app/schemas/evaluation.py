from pydantic import BaseModel, Field
from core.enums import MetricName


class EvaluationContext(BaseModel):
    chunk_id: str | None = None
    text: str
    rank: int | None = None
    score: float | None = None
    source: str | None = None


class EvaluationItemInput(BaseModel):
    query_id: str
    question: str
    answer: str
    contexts: list[EvaluationContext]
    ground_truth: str | None = None


class EvaluationRequest(BaseModel):
    dataset_id: str | None = None
    judge_model: str = "gpt-4o-mini"
    metrics: list[MetricName]
    items: list[EvaluationItemInput] | None = None
    dataset_uri: str | None = None
    shard_size: int = Field(default=500, ge=1, le=5000)


class EvaluationCreatedResponse(BaseModel):
    run_id: str
    status: str
    total_items: int
    estimated_cost_usd: float | None = None
