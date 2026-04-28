"""Application configuration with environment-aware settings."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="configs/dev.env",  # overridden dynamically in get_settings()
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "RAG Evaluation Service"
    APP_VERSION: str = Field(
        default="1.0.0",
        validation_alias=AliasChoices("VERSION", "APP_VERSION"),
    )
    DESCRIPTION: str = "A service for evaluating RAG systems."
    API_PREFIX: str = "/api"
    DEBUG_MODE: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEBUG_MODE", "DEBUG"),
    )
    ENVIRONMENT: Environment = Field(
        default=Environment.DEV,
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV"),
    )

    # Server
    DOMAIN: str = "localhost"

    # Database
    DB_PROVIDER: DatabaseProvider = DatabaseProvider.POSTGRESQL

    DATABASE_URL: str | None = None

    POSTGRESQL_USERNAME: str = "admin"
    POSTGRESQL_PASSWORD: str = "admin"
    POSTGRESQL_SERVER: str = "localhost"
    POSTGRESQL_PORT: int = 5432
    POSTGRESQL_DATABASE: str = "db_rag_eval"

    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DATABASE_POOL_RECYCLE: int = Field(default=3600, ge=300)

    SQLITE_URL: str = "sqlite+aiosqlite:///./test.db"

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
    JWT_SECRET_KEY: SecretStr | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, ge=1)
    JWT_CONFIRMATION_TOKEN_EXPIRE_MINUTES: int = Field(default=20, ge=1)

    # CORS
    # Use str field to receive raw env value, then parse in model_validator
    # This avoids pydantic_settings 2.14.0 issue with list[str] + default_factory + env var
    BACKEND_CORS_ORIGINS: str = Field(default="")
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
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
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOGTAIL_API_KEY: SecretStr | None = None
    SENTRY_DSN: str | None = None

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, ge=1)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, ge=1)

    # Feature flags
    FEATURE_SEMANTIC_SEARCH: bool = False
    FEATURE_EMAIL_NOTIFICATIONS: bool = True
    FEATURE_BACKGROUND_TASKS: bool = True

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        value = value.strip().lower()
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
        return aliases.get(value, value)

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
    def parse_cors_origins(self) -> Settings:
        """Parse BACKEND_CORS_ORIGINS string into CORS_ORIGINS list."""
        if self.BACKEND_CORS_ORIGINS:
            self.CORS_ORIGINS = [
                item.strip()
                for item in self.BACKEND_CORS_ORIGINS.split(",")
                if item.strip()
            ]
        return self

    @model_validator(mode="after")
    def validate_environment_rules(self) -> Settings:
        if self.is_production:
            secret = self.SECRET_KEY.get_secret_value()

            if secret.startswith("dev-") or "change-me" in secret.lower():
                raise ValueError("Production SECRET_KEY must be a real secret")

            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard CORS is not allowed in production")

            if self.DEBUG_MODE:
                raise ValueError("DEBUG_MODE must be false in production")

        if self.DB_PROVIDER == DatabaseProvider.SUPABASE and not self.SUPABASE_DB_URL:
            raise ValueError("SUPABASE_DB_URL is required when DB_PROVIDER=supabase")

        return self

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
    def jwt_secret_key(self) -> str:
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
            assert self.SUPABASE_DB_URL is not None
            return self.SUPABASE_DB_URL

        if self.DATABASE_URL:
            return self.DATABASE_URL

        return (
            f"postgresql+asyncpg://{self.POSTGRESQL_USERNAME}:"
            f"{self.POSTGRESQL_PASSWORD}@{self.POSTGRESQL_SERVER}:"
            f"{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DATABASE}"
        )

    def get_database_sync_url(self) -> str:
        return self.get_database_url().replace("+asyncpg", "")


def get_env_file(environment: Environment) -> str:
    return str(Path("configs") / f"{environment.value}.env")


@lru_cache
def get_settings() -> Settings:
    from app.core.config.logging import get_logger

    logger = get_logger(__name__)
    bootstrap_env = Settings(
        _env_file=None,
        ENVIRONMENT="dev",
    ).ENVIRONMENT
    logger.warning("bootstrap_env: %s", bootstrap_env)

    return Settings(_env_file=get_env_file(bootstrap_env))


settings = get_settings()
