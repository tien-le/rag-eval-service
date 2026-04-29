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
