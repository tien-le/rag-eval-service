Below is the structure I recommend for your current repo. It keeps **phase 1 simple**, but does not block future DDD, SOLID, event-driven, database, worker, and multi-provider scaling.

FastAPI officially recommends `APIRouter` for larger apps split across multiple files, so keeping `api/router.py` plus `api/endpoints/*` is a good choice. Docker Compose also supports `depends_on` with health checks, which is useful once you add PostgreSQL, Qdrant, Redis, or workers. ([FastAPI][1])

---

# Target structure

```text
rag-eval-service/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── evaluations.py
│   │       └── health.py
│   ├── application/
│   │   └── evaluation/
│   │       ├── commands.py
│   │       ├── dto.py
│   │       └── service.py
│   ├── domain/
│   │   └── evaluation/
│   │       ├── entities.py
│   │       ├── enums.py
│   │       ├── exceptions.py
│   │       └── ports.py
│   ├── infra/
│   │   ├── ragas/
│   │   │   ├── provider.py
│   │   │   ├── dataset_adapter.py
│   │   │   └── metric_factory.py
│   │   └── db/
│   │       └── README.md
│   ├── schemas/
│   │   └── evaluation.py
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   └── tests/
│       ├── unit/
│       │   ├── test_evaluation_service.py
│       │   └── test_metric_factory.py
│       └── integration/
│           └── test_evaluation_api.py
├── configs/
│   ├── dev.env
│   ├── test.env.example
│   └── prod.env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Remove for phase 1:

```text
app/models/
app/repositories/
app/services/
app/api/endpoints/runs.py
app/api/endpoints/user.py
app/schemas/user_schema.py
app/infra/db/*.py
```

Keep DB files only when you actually add persistence.

Also remove all:

```text
__pycache__/
*.pyc
```

---

# Why this structure

```text
api/             FastAPI endpoints only
schemas/         request/response models
application/     use cases and orchestration
domain/          pure business rules and contracts
infra/           RAGAS, DB, external SDKs
core/            config, dependencies, logging, app exceptions
tests/           unit and integration tests
```

This follows clean architecture:

```text
api → application → domain
             ↓
           infra
```

The domain must not import FastAPI, RAGAS, SQLAlchemy, Qdrant, OpenAI, etc.

---

# Phase 1: Stateless RAGAS retrieval-quality API

Goal:

```text
POST /api/v1/evaluations/retrieval-quality
```

Only evaluate retrieval quality.

Use RAGAS metrics:

```text
context_precision
context_recall
context_entities_recall
```

RAGAS documents Context Precision as a metric for checking whether retrieved contexts are useful for answering a question, and Context Recall as checking whether important information was retrieved. ([Ragas][2])

## Phase 1 files

```text
app/
├── api/
│   ├── router.py
│   └── endpoints/
│       ├── evaluations.py
│       └── health.py
├── application/
│   └── evaluation/
│       └── service.py
├── domain/
│   └── evaluation/
│       ├── enums.py
│       └── ports.py
├── infra/
│   └── ragas/
│       ├── provider.py
│       ├── dataset_adapter.py
│       └── metric_factory.py
├── schemas/
│   └── evaluation.py
├── core/
│   ├── config.py
│   ├── dependencies.py
│   └── exceptions.py
└── main.py
```

## `domain/evaluation/enums.py`

```python
from enum import StrEnum


class RetrievalMetric(StrEnum):
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"
    CONTEXT_ENTITIES_RECALL = "context_entities_recall"
```

## `domain/evaluation/ports.py`

```python
from typing import Protocol


class RetrievalQualityEvaluator(Protocol):
    async def evaluate(
        self,
        question: str,
        contexts: list[str],
        reference_answer: str | None,
        metrics: list[str],
    ) -> dict[str, float | None]:
        ...
```

## `application/evaluation/service.py`

```python
from app.domain.evaluation.ports import RetrievalQualityEvaluator


class EvaluationService:
    def __init__(self, evaluator: RetrievalQualityEvaluator) -> None:
        self.evaluator = evaluator

    async def evaluate_retrieval_quality(
        self,
        question: str,
        contexts: list[str],
        reference_answer: str | None,
        metrics: list[str],
    ) -> dict[str, float | None]:
        if not question.strip():
            raise ValueError("question must not be empty")

        if not contexts:
            raise ValueError("contexts must not be empty")

        return await self.evaluator.evaluate(
            question=question,
            contexts=contexts,
            reference_answer=reference_answer,
            metrics=metrics,
        )
```

## `infra/ragas/metric_factory.py`

```python
from ragas.metrics import (
    context_precision,
    context_recall,
    context_entities_recall,
)

METRIC_MAP = {
    "context_precision": context_precision,
    "context_recall": context_recall,
    "context_entities_recall": context_entities_recall,
}


def build_retrieval_metrics(metric_names: list[str]):
    unknown = set(metric_names) - set(METRIC_MAP)

    if unknown:
        raise ValueError(f"Unsupported retrieval metrics: {sorted(unknown)}")

    return [METRIC_MAP[name] for name in metric_names]
```

## `infra/ragas/dataset_adapter.py`

```python
from datasets import Dataset


def build_retrieval_dataset(
    question: str,
    contexts: list[str],
    reference_answer: str | None,
) -> Dataset:
    return Dataset.from_list(
        [
            {
                "user_input": question,
                "retrieved_contexts": contexts,
                "reference": reference_answer,
            }
        ]
    )
```

## `infra/ragas/provider.py`

```python
import math

from ragas import aevaluate

from app.infra.ragas.dataset_adapter import build_retrieval_dataset
from app.infra.ragas.metric_factory import build_retrieval_metrics


class RagasRetrievalQualityEvaluator:
    async def evaluate(
        self,
        question: str,
        contexts: list[str],
        reference_answer: str | None,
        metrics: list[str],
    ) -> dict[str, float | None]:
        dataset = build_retrieval_dataset(
            question=question,
            contexts=contexts,
            reference_answer=reference_answer,
        )

        ragas_metrics = build_retrieval_metrics(metrics)

        result = await aevaluate(
            dataset=dataset,
            metrics=ragas_metrics,
            raise_exceptions=False,
            show_progress=False,
        )

        row = result.to_pandas().iloc[0]

        scores: dict[str, float | None] = {}

        for metric_name in metrics:
            value = row.get(metric_name)

            if value is None:
                scores[metric_name] = None
            elif isinstance(value, float) and math.isnan(value):
                scores[metric_name] = None
            else:
                scores[metric_name] = float(value)

        return scores
```

## `schemas/evaluation.py`

```python
from pydantic import BaseModel, Field

from app.domain.evaluation.enums import RetrievalMetric


class RetrievalQualityRequest(BaseModel):
    question: str = Field(..., min_length=1)
    contexts: list[str] = Field(..., min_length=1)
    reference_answer: str | None = None
    metrics: list[RetrievalMetric] = Field(
        default_factory=lambda: [
            RetrievalMetric.CONTEXT_PRECISION,
            RetrievalMetric.CONTEXT_RECALL,
        ]
    )


class RetrievalQualityResponse(BaseModel):
    scores: dict[str, float | None]
    details: dict
```

## `core/dependencies.py`

```python
from functools import lru_cache

from app.application.evaluation.service import EvaluationService
from app.infra.ragas.provider import RagasRetrievalQualityEvaluator


@lru_cache
def get_evaluation_service() -> EvaluationService:
    return EvaluationService(
        evaluator=RagasRetrievalQualityEvaluator()
    )
```

## `api/endpoints/evaluations.py`

```python
from fastapi import APIRouter, Depends

from app.application.evaluation.service import EvaluationService
from app.core.dependencies import get_evaluation_service
from app.schemas.evaluation import RetrievalQualityRequest, RetrievalQualityResponse

router = APIRouter()


@router.post(
    "/retrieval-quality",
    response_model=RetrievalQualityResponse,
)
async def evaluate_retrieval_quality(
    request: RetrievalQualityRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> RetrievalQualityResponse:
    scores = await service.evaluate_retrieval_quality(
        question=request.question,
        contexts=request.contexts,
        reference_answer=request.reference_answer,
        metrics=[metric.value for metric in request.metrics],
    )

    return RetrievalQualityResponse(
        scores=scores,
        details={
            "provider": "ragas",
            "metrics": [metric.value for metric in request.metrics],
        },
    )
```

## `api/endpoints/health.py`

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

## `api/router.py`

```python
from fastapi import APIRouter

from app.api.endpoints import evaluations, health

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    evaluations.router,
    prefix="/evaluations",
    tags=["evaluations"],
)
```

## `main.py`

```python
from fastapi import FastAPI

from app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Evaluation Service",
        version="0.1.0",
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
```

---

# Docker Compose for phase 1

For phase 1, only API is required.

```yaml
services:
  rag-eval-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rag-eval-api
    env_file:
      - configs/dev.env
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
    command: >
      uvicorn app.main:app
      --host 0.0.0.0
      --port 8000
      --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Dockerfile:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

# Phase roadmap

## Phase 1 — Stateless retrieval-quality API

```text
Goal:
  Evaluate one request directly with RAGAS.

Keep:
  FastAPI
  RAGAS
  clean architecture
  unit tests
  integration API test

Avoid:
  DB
  workers
  runs
  users
  idempotency
  LangGraph
```

Deliverables:

```text
POST /api/v1/evaluations/retrieval-quality
GET /api/v1/health
```

---

## Phase 2 — Add PostgreSQL run history

Add:

```text
app/domain/evaluation/entities.py
app/domain/evaluation/repositories.py
app/infra/db/session.py
app/infra/db/models/
app/infra/db/repositories/
app/api/endpoints/runs.py
alembic/
```

New tables:

```text
evaluation_runs
evaluation_samples
metric_results
```

New endpoints:

```text
POST /api/v1/evaluations/retrieval-quality
GET  /api/v1/runs/{run_id}
GET  /api/v1/runs/{run_id}/results
```

At this phase, evaluation can still run synchronously, but you persist results.

---

## Phase 3 — Batch evaluation

Add batch request:

```text
POST /api/v1/evaluations/retrieval-quality/batch
```

Add:

```text
evaluation_batches
```

Process 100–1,000 rows in a request, but still avoid distributed workers.

---

## Phase 4 — Background workers

Add Redis and workers.

```text
app/workers/
app/infra/messaging/
```

Workflow:

```text
API creates run
API returns run_id
Worker evaluates
Client polls GET /runs/{run_id}
```

Use Docker Compose health checks and `depends_on` for startup ordering. Compose supports healthcheck-based dependency conditions, which is useful when API/worker require PostgreSQL or Redis to be ready. ([Docker Documentation][3])

---

## Phase 5 — Idempotency

Add:

```text
idempotency_keys
```

Support:

```http
Idempotency-Key: <uuid>
```

Use for:

```text
POST /evaluations/*
```

This prevents duplicate expensive evaluation jobs.

---

## Phase 6 — LLM provider abstraction

Add:

```text
app/domain/providers/
app/infra/llm/
```

Adapters:

```text
ChatOllama
ChatOpenAI
ChatGoogleGenerativeAI
```

Use only when you add metrics requiring judge LLMs.

---

## Phase 7 — Answer-quality metrics

Add RAGAS metrics such as:

```text
faithfulness
response_relevancy
answer_correctness
```

Keep retrieval metrics and answer metrics separated:

```text
/evaluations/retrieval-quality
/evaluations/answer-quality
/evaluations/rag-quality
```

---

## Phase 8 — LangSmith and Sentry

Add:

```text
app/infra/observability/langsmith.py
app/infra/observability/sentry.py
```

LangSmith is useful for tracing and debugging LLM/RAG execution. Sentry is useful for FastAPI and worker error monitoring. ([LangChain Docs][4])

---

## Phase 9 — LangGraph workflow

Only add LangGraph when runs have multiple durable phases:

```text
validate
embed
retrieve
generate
evaluate
aggregate
persist
```

LangGraph’s durable execution can persist workflow state and resume without reprocessing completed steps, which becomes valuable for long evaluation jobs. ([LangChain Docs][4])

---

## Phase 10 — Large-scale evaluation

For 100K+ rows:

```text
FastAPI only creates jobs
Workers process batches
PostgreSQL stores metadata/results
Object storage stores raw payloads
Qdrant stores vectors
Redis handles locks
```

For 1M+ rows:

```text
partition tables
batch workers
sample expensive RAGAS judge metrics
use cheap retrieval metrics for all rows
```

For 1B rows:

```text
do not use FastAPI workers alone
move execution to Spark/Ray/Flink/Beam
keep FastAPI as control plane
```

---

# Migration from your current tree

## Delete now

```text
app/__pycache__/
app/core/__pycache__/
app/infra/db/__pycache__/
app/schemas/__pycache__/
app/services/__pycache__/
```

Add to `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.env
*.env
!configs/*.env.example
```

## Move files

```text
app/services/evaluation_service.py
→ app/application/evaluation/service.py
```

```text
app/services/ragas_service.py
→ app/infra/ragas/provider.py
```

```text
app/infra/ragas/metric_factory.py
→ keep
```

```text
app/infra/ragas/dataset_adapter.py
→ keep
```

```text
app/routers/*
→ already moved to app/api/endpoints/*
```

```text
app/tests/unittests
→ app/tests/unit
```

```text
app/tests/integration_tests
→ app/tests/integration
```

## Remove from phase 1

```text
app/models/
app/repositories/
app/services/cost_service.py
app/services/idempotency_service.py
app/services/user_service.py
app/api/endpoints/user.py
app/api/endpoints/runs.py
app/schemas/user_schema.py
```

Bring them back later when needed.

---

# Docker Compose by phase

## Phase 1

```yaml
services:
  rag-eval-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - configs/dev.env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Phase 2 with PostgreSQL

```yaml
services:
  rag-eval-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - configs/dev.env
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: rag_eval
      POSTGRES_USER: rag_eval
      POSTGRES_PASSWORD: rag_eval
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag_eval -d rag_eval"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

## Phase 4 with Redis worker

```yaml
services:
  rag-eval-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - configs/dev.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  rag-eval-worker:
    build: .
    env_file:
      - configs/dev.env
    command: celery -A app.workers.celery_app worker --loglevel=INFO
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: rag_eval
      POSTGRES_USER: rag_eval
      POSTGRES_PASSWORD: rag_eval
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag_eval -d rag_eval"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Phase 6+ with Qdrant and Ollama

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  qdrant_data:
  ollama_data:
```

Use Compose profiles for optional services:

```yaml
services:
  qdrant:
    profiles: ["vector"]

  ollama:
    profiles: ["local-llm"]
```

Docker Compose profiles are intended for selectively enabling services for different environments or use cases. ([Docker Documentation][5])

---

# Recommended implementation order

```text
1. Clean repo: remove pycache and unused phase-2 files.
2. Create domain/evaluation/ports.py and enums.py.
3. Move evaluation_service.py to application/evaluation/service.py.
4. Keep RAGAS inside infra/ragas only.
5. Update FastAPI dependencies.
6. Update API router and endpoint.
7. Add unit tests for service and metric factory.
8. Add integration test for POST /api/v1/evaluations/retrieval-quality.
9. Create phase-1 Dockerfile and docker-compose.yml.
10. Add PostgreSQL only in phase 2.
```

Final principle:

```text
Do not build the phase-10 architecture in phase 1.
But make phase 1 boundaries clean enough that phase 10 does not require a rewrite.
```

[1]: https://fastapi.tiangolo.com/tutorial/bigger-applications/?utm_source=chatgpt.com "Bigger Applications - Multiple Files"
[2]: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/?utm_source=chatgpt.com "Context Precision"
[3]: https://docs.docker.com/compose/how-tos/startup-order/?utm_source=chatgpt.com "Control startup and shutdown order in Compose"
[4]: https://docs.langchain.com/oss/python/langgraph/durable-execution?utm_source=chatgpt.com "Durable execution - Docs by LangChain"
[5]: https://docs.docker.com/compose/how-tos/profiles/?utm_source=chatgpt.com "Using profiles with Compose"
