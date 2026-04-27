"""Application configuration with environment-aware settings."""

from functools import lru_cache
import os
from enum import Enum
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environments."""

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class DatabaseProvider(str, Enum):
    """Database provider options."""

    POSTGRESQL = "postgresql"
    SUPABASE = "supabase"
    SQLITE = "sqlite"


def get_environment() -> Environment:
    """Detect current environment from APP_ENV variable.

    Returns:
        Environment enum value

    Environment variable mapping:
        - 'production', 'prod' → PRODUCTION
        - 'staging', 'stage' → STAGING
        - 'test' → TEST
        - anything else → DEV (default)
    """
    env = os.getenv("APP_ENV", "dev").lower()
    match env:
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEV


class Settings(BaseSettings):
    """Application settings with automatic environment variable loading.
    Loads from:
    1. Environment variables
    2. .env file (configs/{environment}.env)
    3. Default values
    """

    # Application
    APP_NAME: str = "RAG Evaluation Service"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "A service for evaluating retrieval-augmented generation (RAG) systems."
    )
    API_PREFIX: str = "/api"
    DEBUG_MODE: bool = False
    ENVIRONMENT: Environment = Field(default_factory=get_environment)

    # Database Provider
    DB_PROVIDER: DatabaseProvider = Field(
        default=DatabaseProvider.POSTGRESQL,
        description="Database provider (supabase, postgresql, sqlite)",
    )

    # Database
    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL database URL (required unless using Supabase)",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=5, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)

    # SQLite
    SQLITE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Qdrant
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None

    # Security
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT encoding",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, ge=1)  # 24 hours

    # JWT Settings (preferred naming)
    JWT_SECRET_KEY: str | None = Field(
        default=None, description="JWT secret key (defaults to SECRET_KEY if not set)"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440, ge=1, description="JWT access token expiration in minutes"
    )
    JWT_CONFIRMATION_TOKEN_EXPIRE_MINUTES: int = Field(
        default=20, ge=1, description="JWT confirmation token expiration in minutes"
    )

    # Supabase
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    SUPABASE_DB_URL: str | None = Field(
        default=None,
        description="Supabase PostgreSQL database URL (used when DB_PROVIDER=supabase)",
    )
    SUPABASE_DB_PASSWORD: str | None = None

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
        ],
    )

    # Email (Mailgun)
    MAILGUN_API_KEY: str | None = None
    MAILGUN_DOMAIN: str | None = None
    MAILGUN_FROM_EMAIL: str = "noreply@example.com"

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_FORMAT: str = Field(default="json", description="Log format (json or console)")

    LOGTAIL_API_KEY: str | None = Field(
        default=None, description="Logtail API key for cloud logging (optional)"
    )

    # Sentry configuration
    SENTRY_DSN: str | None = Field(
        default=None, description="Sentry DSN for error tracking"
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000

    # Feature Flags
    FEATURE_SEMANTIC_SEARCH: bool = False
    FEATURE_EMAIL_NOTIFICATIONS: bool = True
    FEATURE_BACKGROUND_TASKS: bool = True

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=f"configs/{get_environment().value}.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str | None) -> str:
        """Ensure database URL is valid or optional when using Supabase."""
        # Allow empty string or None when using Supabase (will use SUPABASE_DB_URL)
        if not v or v == "":
            return ""
        if not v.startswith(
            ("postgresql://", "postgresql+asyncpg://", "sqlite+aiosqlite://")
        ):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL or SQLite connection string"
            )
        return v

    @field_validator("DB_PROVIDER", mode="before")
    @classmethod
    def validate_db_provider(cls, v: str | DatabaseProvider) -> DatabaseProvider:
        """Parse DB_PROVIDER from string or return enum."""
        if isinstance(v, DatabaseProvider):
            return v
        if isinstance(v, str):
            v_lower = v.lower().strip()
            try:
                return DatabaseProvider(v_lower)
            except ValueError:
                raise ValueError(
                    f"Invalid DB_PROVIDER: {v}. Must be one of: {', '.join([p.value for p in DatabaseProvider])}"
                )
        return DatabaseProvider.POSTGRESQL

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is strong enough."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str | None) -> str | None:
        """Ensure JWT secret key is strong enough if provided."""
        if v is not None and len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters if provided"
            )
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == Environment.DEV

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.ENVIRONMENT == Environment.TEST

    @property
    def jwt_secret_key(self) -> str:
        """Get JWT secret key, falling back to SECRET_KEY if not set."""
        return (
            self.JWT_SECRET_KEY if self.JWT_SECRET_KEY is not None else self.SECRET_KEY
        )

    @property
    def ENV_STATE(self) -> str:
        """Get environment state as string (for compatibility with example code)."""
        return self.ENVIRONMENT.value


class DevConfig(Settings):
    """Development configuration class for isinstance checks."""

    SECRET_KEY: str = Field(
        default="dev-secret-key-minimum-32-characters-long-for-development-only",
        min_length=32,
        description="Secret key for JWT encoding (dev default)",
    )


@lru_cache
def create_settings() -> Settings:
    """Factory function to create environment-specific settings instance.
    Returns:
        DevConfig instance in development, Settings instance otherwise
    """
    env = get_environment()
    if env == Environment.DEV:
        return DevConfig()
    return Settings()


# Global settings instance
settings = create_settings()
