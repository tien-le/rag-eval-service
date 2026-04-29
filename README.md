# RAG Evaluation Quality Microservice

A production-grade, config-driven, event-driven microservice for evaluating RAG, Agentic RAG, workflows, tools, prompts, retrieval quality, guardrails, and LLM behavior.

This project is designed for:

```txt
1K RPM   → single service + Redis + Celery
100K RPM → split services + Kafka + worker pools
1M RPM   → Kubernetes + event backbone + async-first execution
```

---

## 1. Core Architecture Principles

```txt
Workflow = versioned data
Node = reusable code
Config = dynamic and validated
Evaluation = first-class production workflow
Runtime = DB-driven, not file-driven
```

Source-of-truth strategy:

```txt
YAML files        → default configs, templates, GitOps, import/export
PostgreSQL JSONB → runtime workflows and versions
Redis            → cache, rate limits, compiled workflows
Celery           → async jobs, scheduled jobs, retries
Kafka/Redpanda   → high-throughput event stream
LangGraph        → stateful workflow and agent execution
Ragas            → RAG and agentic evaluation
LangSmith        → tracing and observability
```

Runtime rule:

```txt
Runtime should not directly depend on YAML files.
YAML is imported into PostgreSQL before execution.
```

---

## 2. Target Project Structure

```txt
.
├── app
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api
│   │   ├── __init__.py
│   │   ├── deps
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── tenant.py
│   │   │   ├── rate_limit.py
│   │   │   ├── pagination.py
│   │   │   └── tracing.py
│   │   └── routers
│   │       ├── __init__.py
│   │       ├── health_router.py
│   │       ├── workflow_router.py
│   │       ├── eval_router.py
│   │       ├── rag_router.py
│   │       ├── agent_router.py
│   │       ├── prompt_router.py
│   │       ├── job_router.py
│   │       ├── node_config_router.py
│   │       └── admin_router.py
│   │
│   ├── core
│   │   ├── __init__.py
│   │   ├── config
│   │   │   ├── __init__.py
│   │   │   ├── settings.py
│   │   │   ├── env.py
│   │   │   ├── enums.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   ├── observability.py
│   │   │   ├── feature_flags.py
│   │   │   ├── eval_settings.py
│   │   │   ├── llm_settings.py
│   │   │   └── worker_settings.py
│   │   ├── middleware
│   │   │   ├── __init__.py
│   │   │   ├── request_id.py
│   │   │   ├── correlation_id.py
│   │   │   ├── auth_middleware.py
│   │   │   ├── tenant_middleware.py
│   │   │   ├── rate_limit_middleware.py
│   │   │   ├── latency_middleware.py
│   │   │   ├── audit_middleware.py
│   │   │   └── error_middleware.py
│   │   └── security
│   │       ├── __init__.py
│   │       ├── jwt_service.py
│   │       ├── auth0_service.py
│   │       ├── permissions.py
│   │       ├── api_key_service.py
│   │       └── rate_limiter.py
│   │
│   ├── domain
│   │   ├── __init__.py
│   │   │
│   │   ├── workflows
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── registry.py
│   │   │   ├── compiler.py
│   │   │   ├── runner.py
│   │   │   ├── validator.py
│   │   │   ├── versioning.py
│   │   │   ├── import_export.py
│   │   │   ├── config_resolver.py
│   │   │   ├── service.py
│   │   │   └── nodes
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── chunking.py
│   │   │       ├── embedding.py
│   │   │       ├── retrieval.py
│   │   │       ├── reranking.py
│   │   │       ├── generation.py
│   │   │       ├── evaluation.py
│   │   │       ├── guardrails.py
│   │   │       ├── tools.py
│   │   │       └── mcp.py
│   │   │
│   │   ├── evaluation
│   │   │   ├── __init__.py
│   │   │   ├── ragas_runner.py
│   │   │   ├── agent_eval_runner.py
│   │   │   ├── retrieval_eval_runner.py
│   │   │   ├── prompt_eval_runner.py
│   │   │   ├── metrics.py
│   │   │   ├── datasets.py
│   │   │   ├── quality_gates.py
│   │   │   ├── reports.py
│   │   │   └── service.py
│   │   │
│   │   ├── rag
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py
│   │   │   ├── retriever.py
│   │   │   ├── reranker.py
│   │   │   ├── pipeline.py
│   │   │   └── service.py
│   │   │
│   │   ├── agents
│   │   │   ├── __init__.py
│   │   │   ├── state.py
│   │   │   ├── graph_factory.py
│   │   │   ├── nodes.py
│   │   │   ├── edges.py
│   │   │   ├── memory.py
│   │   │   └── service.py
│   │   │
│   │   ├── prompts
│   │   │   ├── __init__.py
│   │   │   ├── registry.py
│   │   │   ├── versioning.py
│   │   │   ├── templates.py
│   │   │   ├── experiments.py
│   │   │   └── service.py
│   │   │
│   │   ├── guardrails
│   │   │   ├── __init__.py
│   │   │   ├── input_guard.py
│   │   │   ├── output_guard.py
│   │   │   ├── pii_redactor.py
│   │   │   ├── prompt_injection.py
│   │   │   └── policy_engine.py
│   │   │
│   │   └── tools
│   │       ├── __init__.py
│   │       ├── registry.py
│   │       ├── base.py
│   │       ├── mcp_client.py
│   │       └── service.py
│   │
│   ├── infra
│   │   ├── __init__.py
│   │   │
│   │   ├── db
│   │   │   ├── __init__.py
│   │   │   ├── session.py
│   │   │   ├── models.py
│   │   │   ├── workflow_repository.py
│   │   │   ├── node_config_repository.py
│   │   │   ├── workflow_run_repository.py
│   │   │   ├── job_repository.py
│   │   │   ├── eval_repository.py
│   │   │   ├── prompt_repository.py
│   │   │   └── vector_store.py
│   │   │
│   │   ├── cache
│   │   │   ├── __init__.py
│   │   │   ├── redis_client.py
│   │   │   ├── workflow_cache.py
│   │   │   ├── response_cache.py
│   │   │   ├── semantic_cache.py
│   │   │   ├── token_bucket.py
│   │   │   └── distributed_lock.py
│   │   │
│   │   ├── llm_gateways
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── router.py
│   │   │   ├── fallback_policy.py
│   │   │   ├── cost_tracker.py
│   │   │   ├── structured_output.py
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   ├── google_provider.py
│   │   │   ├── openrouter_provider.py
│   │   │   └── ollama_provider.py
│   │   │
│   │   ├── event_bus
│   │   │   ├── __init__.py
│   │   │   ├── events.py
│   │   │   ├── publisher.py
│   │   │   ├── consumer.py
│   │   │   ├── redis_streams.py
│   │   │   └── kafka.py
│   │   │
│   │   ├── mcp_gateways
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── registry.py
│   │   │
│   │   └── observability
│   │       ├── __init__.py
│   │       ├── langsmith.py
│   │       ├── otel.py
│   │       ├── metrics.py
│   │       ├── logging.py
│   │       └── tracing.py
│   │
│   ├── workers
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── schedules.py
│   │   ├── retries.py
│   │   ├── dead_letter.py
│   │   └── tasks
│   │       ├── __init__.py
│   │       ├── workflow_tasks.py
│   │       ├── eval_tasks.py
│   │       ├── embedding_tasks.py
│   │       ├── indexing_tasks.py
│   │       ├── agent_tasks.py
│   │       ├── llm_tasks.py
│   │       └── maintenance_tasks.py
│   │
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── workflow.py
│   │   ├── eval.py
│   │   ├── rag.py
│   │   ├── agent.py
│   │   ├── prompt.py
│   │   └── job.py
│   │
│   └── utils
│       ├── __init__.py
│       ├── hashing.py
│       ├── json.py
│       ├── yaml.py
│       ├── time.py
│       └── ids.py
│
├── configs
│   ├── env
│   │   ├── dev.env
│   │   ├── test.env
│   │   ├── staging.env
│   │   ├── preprod.env
│   │   ├── prod.env.example
│   │   └── local.env.example
│   ├── nodes
│   │   ├── chunking.yml
│   │   ├── embedding.yml
│   │   ├── retrieval.yml
│   │   ├── reranking.yml
│   │   ├── generation.yml
│   │   ├── evaluation.yml
│   │   ├── guardrails.yml
│   │   └── tools.yml
│   ├── workflow_templates
│   │   ├── rag_basic.yml
│   │   ├── rag_with_rerank.yml
│   │   ├── agentic_rag.yml
│   │   ├── document_indexing.yml
│   │   └── rag_eval.yml
│   ├── eval
│   │   ├── dev.yml
│   │   ├── test.yml
│   │   ├── staging.yml
│   │   ├── preprod.yml
│   │   └── prod.yml
│   ├── prompts
│   │   ├── rag_answer.v1.yml
│   │   ├── agent_planner.v1.yml
│   │   └── judge_prompt.v1.yml
│   ├── policies
│   │   ├── guardrails.yml
│   │   ├── pii.yml
│   │   ├── tenant_quotas.yml
│   │   ├── model_allowlist.yml
│   │   └── rate_limits.yml
│   └── workers
│       ├── dev.yml
│       ├── test.yml
│       ├── staging.yml
│       ├── preprod.yml
│       └── prod.yml
│
├── migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions
│
├── scripts
│   ├── seed_node_configs.py
│   ├── import_workflow.py
│   ├── export_workflow.py
│   ├── validate_workflow.py
│   ├── diff_workflow.py
│   ├── promote_workflow.py
│   └── run_offline_eval.py
│
├── tests
│   ├── unit
│   ├── integration
│   ├── contract
│   ├── load
│   └── eval
│
├── docs
│   ├── architecture.md
│   ├── workflow-format.md
│   ├── eval-strategy.md
│   ├── deployment.md
│   └── runbooks.md
│
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

---

## 3. Important Responsibilities by Layer

### API layer

FastAPI routers should only handle:

```txt
request validation
auth dependency
calling domain services
returning response models
```

Do not put business logic inside routers.

---

### Domain layer

The domain layer owns:

```txt
workflow validation
workflow execution
RAG logic
agent logic
evaluation logic
prompt versioning
guardrail policies
tool registry
```

This layer should not depend directly on FastAPI.

---

### Infra layer

The infra layer owns:

```txt
PostgreSQL
Redis
Kafka
Celery
LLM providers
MCP clients
LangSmith
OpenTelemetry
Vector DB
```

---

### Worker layer

Celery workers own:

```txt
long-running workflow execution
batch evaluations
scheduled evaluations
embedding jobs
indexing jobs
agent jobs
retryable external calls
maintenance jobs
```

---

## 4. Runtime Data Flow

```txt
Client
  ↓
FastAPI router
  ↓
Auth0/JWT + tenant middleware
  ↓
Rate limiter
  ↓
Workflow service
  ↓
Load workflow JSONB from PostgreSQL
  ↓
Resolve configs
  ↓
Validate workflow
  ↓
Use Redis compiled workflow cache if available
  ↓
Run sequential runner or LangGraph runner
  ↓
Call nodes
  ↓
Call LLM gateway
  ↓
Run Ragas / evaluation nodes
  ↓
Store run + step results
  ↓
Emit events
  ↓
Trace to LangSmith
```

---

## 5. Async Data Flow

```txt
Client
  ↓
POST /v1/workflows/{id}/run-async
  ↓
Create async_jobs row
  ↓
Dispatch Celery task
  ↓
Worker loads workflow version
  ↓
Worker executes workflow
  ↓
Worker stores results
  ↓
Worker emits events
  ↓
Client polls GET /v1/jobs/{job_id}
```

---

## 6. Celery Queues

```txt
workflow
evaluation
embedding
indexing
agent
llm
maintenance
dead_letter
```

Recommended routing:

```python
task_routes = {
    "workflow.run": {"queue": "workflow"},
    "eval.run": {"queue": "evaluation"},
    "embedding.batch": {"queue": "embedding"},
    "indexing.upsert": {"queue": "indexing"},
    "agent.run": {"queue": "agent"},
    "maintenance.cleanup": {"queue": "maintenance"},
}
```

---

## 7. Kafka / Event Topics

Use Celery for jobs. Use Kafka or Redpanda for high-throughput event streaming.

```txt
workflow.run.requested
workflow.run.started
workflow.step.started
workflow.step.completed
workflow.run.completed
workflow.run.failed

eval.requested
eval.started
eval.completed
eval.failed

llm.call.started
llm.call.completed
llm.call.failed

guardrail.violation.detected
prompt.version.published
node.config.updated
dataset.version.published
```

---

## 8. PostgreSQL Tables

Minimum required tables:

```txt
workflow_definitions
workflow_versions
node_config_defaults
tenant_node_configs
workflow_runs
workflow_step_runs
async_jobs
eval_runs
eval_scores
prompt_definitions
prompt_versions
datasets
dataset_versions
llm_call_logs
audit_logs
```

---

## 9. Workflow Tables

```sql
CREATE TABLE workflow_definitions (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    workflow_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    current_version_id UUID,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE workflow_versions (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflow_definitions(id),
    version INT NOT NULL,
    definition_json JSONB NOT NULL,
    definition_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT,
    changelog TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ
);

CREATE TABLE node_config_defaults (
    id UUID PRIMARY KEY,
    node_type TEXT NOT NULL,
    implementation TEXT NOT NULL,
    default_config JSONB NOT NULL,
    schema_json JSONB NOT NULL,
    version INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    workflow_id UUID NOT NULL,
    workflow_version_id UUID NOT NULL,
    input_json JSONB NOT NULL,
    output_json JSONB,
    status TEXT NOT NULL,
    trace_id TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    error TEXT
);

CREATE TABLE workflow_step_runs (
    id UUID PRIMARY KEY,
    workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id),
    step_id TEXT NOT NULL,
    input_json JSONB,
    output_json JSONB,
    latency_ms INT,
    token_usage JSONB,
    cost_usd NUMERIC,
    status TEXT NOT NULL,
    error TEXT
);
```

---

## 10. Async Job Table

```sql
CREATE TABLE async_jobs (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    celery_task_id TEXT,
    input_json JSONB,
    output_json JSONB,
    error TEXT,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

---

## 11. Workflow JSON Format

```json
{
  "id": "rag_eval_support",
  "version": 1,
  "input_schema": "RagEvalInput",
  "output_schema": "RagEvalOutput",
  "steps": [
    {
      "id": "chunk",
      "type": "chunking",
      "implementation": "recursive_text_splitter",
      "config_ref": "chunking.default",
      "config_override": {
        "chunk_size": 1200,
        "chunk_overlap": 200
      }
    },
    {
      "id": "embed",
      "type": "embedding",
      "implementation": "openai_embedding",
      "config_ref": "embedding.default"
    },
    {
      "id": "retrieve",
      "type": "retrieval",
      "implementation": "vector_retrieval",
      "config_override": {
        "top_k": 8
      }
    },
    {
      "id": "evaluate",
      "type": "evaluation",
      "implementation": "ragas_eval",
      "config_override": {
        "metrics": [
          "faithfulness",
          "answer_relevancy",
          "context_precision",
          "context_recall"
        ]
      }
    }
  ],
  "edges": [
    {"from": "chunk", "to": "embed"},
    {"from": "embed", "to": "retrieve"},
    {"from": "retrieve", "to": "evaluate"}
  ],
  "quality_gates": {
    "faithfulness": 0.85,
    "answer_relevancy": 0.8,
    "context_precision": 0.75,
    "context_recall": 0.75
  }
}
```

---

## 12. Config Resolution Order

Effective config should be resolved in this order:

```txt
1. Global YAML node default
2. DB node default
3. Tenant node default
4. Workflow config_ref
5. Workflow config_override
6. Runtime override, if allowed
```

Example:

```python
def resolve_config(
    node_default: dict,
    tenant_default: dict,
    workflow_config: dict,
    runtime_override: dict | None = None,
) -> dict:
    return deep_merge(
        node_default,
        tenant_default,
        workflow_config,
        runtime_override or {},
    )
```

---

## 13. Workflow Node Interface

Every node must implement the same interface.

```python
from typing import Any, Protocol

class WorkflowNode(Protocol):
    async def run(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        ...
```

Node examples:

```txt
recursive_text_splitter
markdown_header_splitter
openai_embedding
ollama_embedding
vector_retrieval
hybrid_retrieval
cross_encoder_reranker
llm_generation
ragas_eval
input_guardrail
output_guardrail
mcp_tool_call
```

---

## 14. Workflow Registry

```python
NODE_REGISTRY = {
    "recursive_text_splitter": RecursiveTextSplitterNode(),
    "markdown_header_splitter": MarkdownHeaderSplitterNode(),
    "openai_embedding": OpenAIEmbeddingNode(),
    "vector_retrieval": VectorRetrievalNode(),
    "hybrid_retrieval": HybridRetrievalNode(),
    "cross_encoder_reranker": CrossEncoderRerankerNode(),
    "llm_generation": LLMGenerationNode(),
    "ragas_eval": RagasEvalNode(),
    "input_guardrail": InputGuardrailNode(),
    "output_guardrail": OutputGuardrailNode(),
    "mcp_tool_call": MCPToolCallNode(),
}
```

---

## 15. Workflow Runner

Use lightweight runner for simple sequential workflows.

```python
class WorkflowRunner:
    def __init__(self, registry, config_resolver, tracer):
        self.registry = registry
        self.config_resolver = config_resolver
        self.tracer = tracer

    async def run(self, workflow: dict, input_data: dict, context: dict):
        state = input_data

        for step in workflow["steps"]:
            node = self.registry[step["implementation"]]
            config = await self.config_resolver.resolve(step, context)

            with self.tracer.step(step["id"]):
                state = await node.run(
                    input_data=state,
                    config=config,
                    context=context,
                )

        return state
```

Use LangGraph when workflow needs:

```txt
conditional edges
agent loops
tool calls
state checkpointing
human-in-the-loop
retries per edge
long-running execution
```

---

## 16. Import / Export Workflow

Import flow:

```txt
YAML file
  ↓
parse
  ↓
validate schema
  ↓
normalize to canonical JSON
  ↓
calculate definition_hash
  ↓
compare with current DB version
  ↓
create draft workflow version
  ↓
optionally publish
```

Export flow:

```txt
DB workflow version
  ↓
canonical JSON
  ↓
optional config ref resolution
  ↓
YAML file
```

Published workflow versions are immutable.

```txt
draft      = editable
published  = immutable
archived   = read-only
```

---

## 17. API Endpoints

```txt
GET  /health
GET  /ready

POST /v1/workflows
GET  /v1/workflows
GET  /v1/workflows/{workflow_id}
POST /v1/workflows/{workflow_id}/validate
POST /v1/workflows/{workflow_id}/dry-run
POST /v1/workflows/{workflow_id}/publish
POST /v1/workflows/{workflow_id}/rollback
POST /v1/workflows/{workflow_id}/run
POST /v1/workflows/{workflow_id}/run-async
GET  /v1/workflows/{workflow_id}/export.yaml
POST /v1/workflows/import

GET  /v1/jobs/{job_id}
POST /v1/jobs/{job_id}/cancel
POST /v1/jobs/{job_id}/retry
POST /v1/jobs/{job_id}/replay

POST /v1/evaluations/run
POST /v1/evaluations/batch
GET  /v1/evaluations/{run_id}
GET  /v1/evaluations/{run_id}/report

GET  /v1/node-configs
POST /v1/node-configs/seed
POST /v1/node-configs/validate

GET  /v1/prompts
POST /v1/prompts
POST /v1/prompts/{prompt_id}/publish

GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/steps
```

---

## 18. LLM Gateway

All model calls must go through the LLM gateway.

```python
class LLMProvider(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResponse:
        ...

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        ...

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        ...
```

Gateway responsibilities:

```txt
provider routing
fallback policy
timeouts
retries
circuit breakers
model allowlist
tenant quota
token accounting
cost accounting
structured output
LangSmith tracing
```

Supported providers:

```txt
OpenAI
Anthropic
Google
OpenRouter
Ollama
```

---

## 19. Evaluation System

Evaluation types:

```txt
retrieval evaluation
generation evaluation
agent trajectory evaluation
tool selection evaluation
prompt version evaluation
online sampled production evaluation
offline regression evaluation
```

Common RAG metrics:

```txt
faithfulness
answer relevancy
context precision
context recall
context relevance
hallucination risk
```

Each eval result must store:

```txt
workflow_version_id
prompt_version_id
dataset_version_id
model_provider
model_name
metric_name
metric_score
trace_id
run_id
```

---

## 20. Environment Strategy

```txt
dev
├── cheap models
├── verbose logs
├── local Redis
├── local Postgres
├── local vector DB
└── relaxed thresholds

test
├── deterministic mocks
├── no real LLM calls by default
├── frozen datasets
├── fixed seeds
└── strict contract tests

staging
├── production-like infra
├── sampled real traces
├── synthetic load tests
└── non-blocking eval alerts

preprod
├── same models as prod
├── same thresholds as prod
├── release-gating evals
├── shadow traffic
└── full observability

prod
├── strict quotas
├── online sampled eval
├── model fallback
├── cost controls
├── alerting
└── audit logs
```

---

## 21. Observability

Required observability:

```txt
structured JSON logs
request IDs
correlation IDs
trace IDs
LangSmith traces
OpenTelemetry metrics
workflow step metrics
LLM token metrics
LLM cost metrics
cache hit metrics
rate-limit metrics
eval score metrics
```

Every workflow step should record:

```txt
step_id
input hash
output hash
latency
status
error
token usage
cost
cache hit
trace id
```

---

## 22. Middleware

Required FastAPI middleware:

```txt
request_id
correlation_id
tenant resolver
Auth0/JWT validation
RBAC permissions
rate limiter
body size guard
latency tracker
audit logger
exception mapper
CORS
OpenTelemetry tracing
```

---

## 23. Guardrails

Guardrails should exist at multiple levels:

```txt
request guardrails
prompt guardrails
tool guardrails
retrieval guardrails
LLM output guardrails
PII redaction
prompt injection detection
policy enforcement
```

Guardrail violations should emit:

```txt
guardrail.violation.detected
```

---

## 24. Prompt Versioning

Prompts are versioned independently from workflows.

```txt
prompt_definitions
prompt_versions
prompt_experiments
prompt_eval_results
```

Prompt version must be stored with:

```txt
workflow_run
eval_run
llm_call_log
```

---

## 25. Dataset Versioning

Datasets are versioned independently.

```txt
datasets
dataset_versions
dataset_samples
dataset_labels
```

Dataset types:

```txt
golden dataset
regression dataset
synthetic dataset
tenant dataset
production sampled traces
```

---

## 26. Release Gates

CI/CD should run:

```txt
unit tests
integration tests
contract tests
workflow schema validation
YAML config validation
offline RAG evaluation
prompt regression evaluation
security checks
load tests
```

Block deployment if:

```txt
quality score drops below threshold
latency exceeds threshold
cost exceeds threshold
critical workflow validation fails
```

Example:

```yaml
quality_gate:
  min_faithfulness: 0.85
  min_answer_relevancy: 0.80
  min_context_precision: 0.75
  min_context_recall: 0.75
  max_latency_p95_ms: 5000
  max_cost_per_1000_runs_usd: 10
  block_release_on_failure: true
```

---

## 27. Scaling Strategy

### 1K RPM

```txt
FastAPI
PostgreSQL
Redis
Vector DB
Celery workers
LangSmith
```

### 100K RPM

```txt
API gateway
workflow service
evaluation service
LLM gateway
Redis cluster
Kafka / Redpanda
Celery worker pools
vector DB cluster
```

### 1M RPM

```txt
global load balancer
regional API gateways
Kubernetes
HPA/KEDA
Kafka backbone
tenant-aware sharding
multi-region Redis
async-first execution
strict quotas
DLQ
backpressure
```

---

## 28. Implementation Roadmap

### Phase 1: Foundation

Implement:

```txt
FastAPI app
settings management
health checks
PostgreSQL session
Redis client
JWT/Auth0
logging
request ID middleware
basic error handling
```

Files:

```txt
app/main.py
app/core/config/settings.py
app/core/config/logging.py
app/infra/db/session.py
app/infra/cache/redis_client.py
app/api/routers/health_router.py
```

---

### Phase 2: Workflow Schema

Implement:

```txt
WorkflowDefinition schema
WorkflowStep schema
WorkflowEdge schema
Workflow validation
workflow hash calculation
```

Files:

```txt
app/domain/workflows/schemas.py
app/domain/workflows/validator.py
app/utils/hashing.py
```

---

### Phase 3: Node Registry

Implement:

```txt
WorkflowNode protocol
node registry
basic chunking node
basic embedding node
basic evaluation node
```

Files:

```txt
app/domain/workflows/nodes/base.py
app/domain/workflows/nodes/chunking.py
app/domain/workflows/nodes/embedding.py
app/domain/workflows/nodes/evaluation.py
app/domain/workflows/registry.py
```

---

### Phase 4: DB Persistence

Implement:

```txt
workflow_definitions
workflow_versions
node_config_defaults
workflow_runs
workflow_step_runs
repositories
Alembic migrations
```

Files:

```txt
app/infra/db/models.py
app/infra/db/workflow_repository.py
app/infra/db/node_config_repository.py
app/infra/db/workflow_run_repository.py
migrations/versions/*
```

---

### Phase 5: Config Import / Export

Implement:

```txt
load YAML defaults
seed node configs
import workflow YAML to DB
export DB workflow to YAML
validate before import
```

Files:

```txt
app/domain/workflows/import_export.py
scripts/seed_node_configs.py
scripts/import_workflow.py
scripts/export_workflow.py
```

---

### Phase 6: Workflow Runner

Implement:

```txt
config resolver
sequential workflow runner
workflow run persistence
step run persistence
workflow execution API
```

Files:

```txt
app/domain/workflows/config_resolver.py
app/domain/workflows/runner.py
app/domain/workflows/service.py
app/api/routers/workflow_router.py
```

---

### Phase 7: LLM Gateway

Implement:

```txt
LLM provider protocol
OpenAI provider
Ollama provider
provider router
fallback policy
cost tracker
structured output
```

Files:

```txt
app/infra/llm_gateways/base.py
app/infra/llm_gateways/router.py
app/infra/llm_gateways/openai_provider.py
app/infra/llm_gateways/ollama_provider.py
app/infra/llm_gateways/fallback_policy.py
app/infra/llm_gateways/cost_tracker.py
```

---

### Phase 8: Ragas Evaluation

Implement:

```txt
Ragas evaluation runner
retrieval metrics
generation metrics
quality gates
evaluation reports
```

Files:

```txt
app/domain/evaluation/ragas_runner.py
app/domain/evaluation/metrics.py
app/domain/evaluation/quality_gates.py
app/domain/evaluation/reports.py
app/api/routers/eval_router.py
```

---

### Phase 9: Celery Workers

Implement:

```txt
Celery app
workflow async task
eval async task
embedding async task
job status table
job router
retry policies
DLQ handler
```

Files:

```txt
app/workers/celery_app.py
app/workers/tasks/workflow_tasks.py
app/workers/tasks/eval_tasks.py
app/workers/tasks/embedding_tasks.py
app/workers/retries.py
app/workers/dead_letter.py
app/api/routers/job_router.py
```

---

### Phase 10: Event Bus

Implement:

```txt
event schema
publisher
Kafka or Redis Streams backend
workflow events
eval events
LLM call events
guardrail events
```

Files:

```txt
app/infra/event_bus/events.py
app/infra/event_bus/publisher.py
app/infra/event_bus/kafka.py
app/infra/event_bus/redis_streams.py
```

---

### Phase 11: LangGraph Runtime

Implement:

```txt
workflow to LangGraph compiler
agent state
conditional edges
checkpoint store
agent tool nodes
```

Files:

```txt
app/domain/workflows/compiler.py
app/domain/agents/state.py
app/domain/agents/graph_factory.py
app/domain/agents/nodes.py
app/domain/agents/edges.py
app/domain/agents/memory.py
```

---

### Phase 12: Observability

Implement:

```txt
LangSmith tracing
OpenTelemetry
structured logs
metrics
cost tracking
trace propagation
```

Files:

```txt
app/infra/observability/langsmith.py
app/infra/observability/otel.py
app/infra/observability/metrics.py
app/infra/observability/logging.py
```

---

### Phase 13: Production Hardening

Implement:

```txt
idempotency keys
distributed locks
rate limits
tenant quotas
feature flags
audit logs
backup strategy
retention policy
admin replay tools
```

Files:

```txt
app/infra/cache/distributed_lock.py
app/core/config/feature_flags.py
app/infra/db/job_repository.py
app/api/routers/admin_router.py
```

---

## 29. Testing Strategy

```txt
unit tests
├── node tests
├── config resolver tests
├── workflow validator tests
├── LLM gateway tests

integration tests
├── Postgres
├── Redis
├── Celery
├── workflow run
├── eval run

contract tests
├── API schemas
├── workflow JSON schema
├── event schema

eval tests
├── golden dataset
├── regression dataset
├── prompt comparison

load tests
├── sync workflow endpoint
├── async workflow endpoint
├── evaluation endpoint
```

---

## 30. Makefile Targets

```makefile
install:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn app.main:app --reload

worker:
	celery -A app.workers.celery_app worker -l info

beat:
	celery -A app.workers.celery_app beat -l info

test:
	pytest

lint:
	ruff check app tests

format:
	ruff format app tests

migrate:
	alembic upgrade head

seed-configs:
	python scripts/seed_node_configs.py

import-workflow:
	python scripts/import_workflow.py

export-workflow:
	python scripts/export_workflow.py
```

---

## 31. Docker Compose Services

Recommended local services:

```txt
api
worker
beat
postgres
redis
qdrant
kafka
zookeeper or redpanda
otel-collector
prometheus
grafana
```

---

## 32. Critical Rules for Cursor Implementation

```txt
1. Do not put business logic in FastAPI routers.
2. Do not hardcode workflows in Python.
3. Do not execute workflows directly from YAML at runtime.
4. Do not mutate published workflow versions.
5. Every workflow run must store workflow_version_id.
6. Every eval result must store workflow_version_id, prompt_version_id, dataset_version_id, and model name.
7. Every LLM call must go through the LLM Gateway.
8. Every workflow step must be traceable.
9. Every external call must have timeout, retry, and circuit breaker policy.
10. Every production endpoint must be tenant-aware.
11. Every async job must have idempotency support.
12. Every failed job must be retryable or moved to DLQ.
13. Every workflow config must be validated before publish.
14. Every node must implement WorkflowNode.
15. Complex workflows should compile into LangGraph.
```

---

## 33. Final Architecture Summary

```txt
FastAPI accepts requests.
PostgreSQL stores runtime workflows.
Redis caches hot state.
Celery executes async work.
Kafka streams high-volume events.
LangGraph runs complex workflows and agents.
Ragas evaluates quality.
LangSmith traces execution.
LLM Gateway controls all model providers.
```

The final system is:

```txt
config-driven
event-driven
tenant-aware
versioned
observable
reproducible
scalable
evaluation-first
```
