"""Application configuration with environment-aware settings."""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class DatabaseProvider(StrEnum):
    POSTGRESQL = "postgresql"
    SUPABASE = "supabase"
    SQLITE = "sqlite"


def parse_environment(value: str | None) -> Environment:
    raw = (value or "dev").strip().lower()

    aliases = {
        "development": Environment.DEV,
        "dev": Environment.DEV,
        "prod": Environment.PRODUCTION,
        "production": Environment.PRODUCTION,
        "stage": Environment.STAGING,
        "staging": Environment.STAGING,
        "test": Environment.TEST,
        "testing": Environment.TEST,
    }

    return aliases.get(raw, Environment.DEV)


def get_env_file(environment: Environment) -> Path:
    return Path("configs") / f"{environment.value}.env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "RAG Evaluation Service"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "A service for evaluating RAG systems."
    API_PREFIX: str = "/api"
    DEBUG_MODE: bool = False
    ENVIRONMENT: Environment = Environment.DEV

    # Server
    DOMAIN: str = "localhost"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Database
    DB_PROVIDER: DatabaseProvider = DatabaseProvider.POSTGRESQL
    DATABASE_URL: str | None = None

    POSTGRESQL_USERNAME: str = "admin"
    POSTGRESQL_PASSWORD: SecretStr = SecretStr("admin")
    POSTGRESQL_SERVER: str = "localhost"
    POSTGRESQL_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRESQL_DATABASE: str = "db_rag_eval"

    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DATABASE_POOL_RECYCLE: int = Field(default=3600, ge=300)

    SQLITE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_USER_NAME: str = "default"
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_SSL: bool = True
    REDIS_URL: str | None = None

    # Supabase
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: SecretStr | None = None
    SUPABASE_DB_URL: str | None = None
    SUPABASE_DB_PASSWORD: SecretStr | None = None

    # Qdrant
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: SecretStr | None = None

    # Security / JWT
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("dev-secret-key-minimum-32-characters-long-only"),
        min_length=32,
    )
    JWT_SECRET_KEY: SecretStr | None = SecretStr("dev-change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)
    JWT_CONFIRMATION_TOKEN_EXPIRE_MINUTES: int = Field(default=10, ge=1)

    # Admin credentials (for initial setup)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: SecretStr = SecretStr("admin")
    DEFAULT_TENANT_ID: str = "default"

    # LLM Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "ollama"] = "ollama"
    DEFAULT_GENERATION_MODEL_NAME: str = "qwen2.5:latest"
    DEFAULT_EMBEDDINGS_MODEL_NAME: str = "nomic-embed-text:latest"

    # https://openrouter.ai/openai
    GENERATION_MODEL: str = "gpt-5.4-mini"  # openai/gpt-5.4-nano
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    PGVECTOR_COLLECTION: str = "knowledge_base"
    # Enable when PostgreSQL has pgvector extension support
    # (e.g., pgvector/pgvector image). Off by default for local Postgres.
    PGVECTOR_ENABLED: bool = False

    # Research Tools
    TAVILY_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("TAVILY_API_KEY", "TAVILY_KEY"),
    )

    # Observability
    LANGCHAIN_TRACING_V2: bool = True
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "lavie"
    OTEL_EXPORTER_ENDPOINT: str = ""

    # MCP
    # MCP_SERVERS: list[MCPServerSpec] = Field(default_factory=list)

    # Prompt assets (resolved under app/)
    PROMPT_ASSETS_DIR: str | None = None
    PROMPT_REGISTRY_PATH: str | None = None

    # Agent context (approximate tokenizer units via LangChain trim_messages)
    # Mirrors recommended defaults in ``agent_orchestration.domain.memory_budget`` /
    # ``tool_execution_policy``. Set to 0 to disable trimming / caps for that path.
    AGENT_MAX_CONTEXT_TOKENS: int = 12_000
    SUPERVISOR_ROUTING_MAX_TOKENS: int = 2_048
    MAX_TOOL_OUTPUT_CHARS: int = 10_000
    MEMORY_SUMMARIZATION_TRIGGER_MESSAGES: int = 40
    MEMORY_SUMMARIZATION_KEEP_RECENT_MESSAGES: int = 12
    MEMORY_SUMMARY_MAX_CHARS: int = 4_000
    MEMORY_SUMMARIZER_PROVIDER: Literal["openai", "anthropic", "gemini", ""] = ""
    MEMORY_SUMMARIZER_MODEL_NAME: str = ""

    # Celery (v1 — Redis broker)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Kafka (v2 — 100K RPM tier, opt-in)
    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_EVAL_REQUESTED: str = "eval.requested"
    KAFKA_TOPIC_EVAL_COMPLETED: str = "eval.completed"
    KAFKA_TOPIC_EVAL_FAILED: str = "eval.failed"
    KAFKA_CONSUMER_GROUP_ID: str = "eval-workers"

    # CORS
    BACKEND_CORS_ORIGINS: str = ""
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
        ],
    )

    # Email
    MAILGUN_API_KEY: SecretStr | None = None
    MAILGUN_DOMAIN: str | None = None
    MAILGUN_FROM_EMAIL: str = "noreply@example.com"

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_FORMAT: str = Field(default="json", description="Log format (json or console)")

    LOGTAIL_API_KEY: SecretStr | None = None
    SENTRY_DSN: str | None = Field(
        default=None, description="Sentry DSN for error tracking"
    )

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)
    RATE_LIMIT_PER_HOUR: int = Field(default=2, ge=1)

    # Feature flags
    FEATURE_SEMANTIC_SEARCH: bool = False
    FEATURE_EMAIL_NOTIFICATIONS: bool = True
    FEATURE_BACKGROUND_TASKS: bool = True

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, value: Any) -> Environment | Any:
        if isinstance(value, str):
            return parse_environment(value)
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        value = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        if value not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")

        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str | None) -> str | None:
        if not value:
            return None

        allowed_prefixes = (
            "postgresql://",
            "postgresql+asyncpg://",
            "sqlite+aiosqlite://",
        )

        if not value.startswith(allowed_prefixes):
            raise ValueError(
                "DATABASE_URL must start with postgresql://, "
                "postgresql+asyncpg://, or sqlite+aiosqlite://"
            )

        return value

    @model_validator(mode="after")
    def normalize_cors_origins(self) -> Settings:
        if self.BACKEND_CORS_ORIGINS:
            self.CORS_ORIGINS = [
                origin.strip()
                for origin in self.BACKEND_CORS_ORIGINS.split(",")
                if origin.strip()
            ]

        return self

    @model_validator(mode="after")
    def validate_environment_rules(self) -> Settings:
        if self.is_production:
            secret = self.SECRET_KEY.get_secret_value()

            if secret.startswith("dev-") or "change-me" in secret.lower():
                raise ValueError("Production SECRET_KEY must be a real secret")

            if self.DEBUG_MODE:
                raise ValueError("DEBUG_MODE must be false in production")

            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard CORS is not allowed in production")

        if self.DB_PROVIDER == DatabaseProvider.SUPABASE and not self.SUPABASE_DB_URL:
            raise ValueError("SUPABASE_DB_URL is required when DB_PROVIDER=supabase")
        return self

    @property
    def is_otel_enabled(self) -> bool:
        return bool(self.OTEL_EXPORTER_ENDPOINT and self.OTEL_EXPORTER_ENDPOINT.strip())

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEV

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == Environment.TEST

    @property
    def resolved_jwt_secret(self) -> str:
        """Returns the effective JWT secret, falling back to SECRET_KEY."""
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY.get_secret_value()
        return self.SECRET_KEY.get_secret_value()

    @property
    def ENV_STATE(self) -> str:
        return str(self.ENVIRONMENT)

    def get_database_url(self) -> str:
        if self.DB_PROVIDER == DatabaseProvider.SQLITE:
            return self.SQLITE_URL

        if self.DB_PROVIDER == DatabaseProvider.SUPABASE:
            if not self.SUPABASE_DB_URL:
                raise ValueError("SUPABASE_DB_URL is required")
            return self.SUPABASE_DB_URL

        if self.DATABASE_URL:
            return self.DATABASE_URL

        password = quote_plus(self.POSTGRESQL_PASSWORD.get_secret_value())

        return (
            f"postgresql+asyncpg://{self.POSTGRESQL_USERNAME}:"
            f"{password}@{self.POSTGRESQL_SERVER}:"
            f"{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DATABASE}"
        )

    def get_database_sync_url(self) -> str:
        return self.get_database_url().replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    environment = parse_environment(os.getenv("APP_ENV") or os.getenv("ENVIRONMENT"))
    env_file = get_env_file(environment)
    return Settings(
        _env_file=env_file if env_file.exists() else None,
        ENVIRONMENT=environment,
    )


settings = get_settings()
