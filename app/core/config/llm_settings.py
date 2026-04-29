"""LLM provider settings configuration."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM gateway configuration settings."""

    # OpenAI
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_ORG_ID: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"

    # Anthropic
    ANTHROPIC_API_KEY: SecretStr | None = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"

    # Google (Gemini)
    GOOGLE_API_KEY: SecretStr | None = None
    GOOGLE_BASE_URL: str = "https://generativelanguage.googleapis.com"
    GOOGLE_DEFAULT_MODEL: str = "gemini-1.5-flash"

    # OpenRouter
    OPENROUTER_API_KEY: SecretStr | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "openai/gpt-4o-mini"

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.2"
    OLLAMA_ENABLED: bool = True

    # Global LLM settings
    LLM_DEFAULT_TIMEOUT: int = Field(default=60, ge=1, le=300)
    LLM_MAX_RETRIES: int = Field(default=3, ge=0, le=10)
    LLM_RETRY_DELAY: float = Field(default=1.0, ge=0)
    LLM_CIRCUIT_BREAKER_THRESHOLD: int = Field(default=5, ge=1)
    LLM_CIRCUIT_BREAKER_RECOVERY: int = Field(default=30, ge=1)

    # Cost tracking
    LLM_COST_TRACKING_ENABLED: bool = True
    LLM_COST_ALERT_THRESHOLD: float = 100.0  # USD per day

    # Model allowlist (comma-separated list of allowed models)
    LLM_MODEL_ALLOWLIST: str = "*"  # * means all allowed

    class Config:
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_allowed_models(self) -> list[str] | None:
        """Get list of allowed models. Returns None if all allowed."""
        if self.LLM_MODEL_ALLOWLIST == "*":
            return None
        return [m.strip() for m in self.LLM_MODEL_ALLOWLIST.split(",") if m.strip()]

    def is_model_allowed(self, model: str) -> bool:
        """Check if a model is in the allowlist."""
        allowed = self.get_allowed_models()
        if allowed is None:
            return True
        return model in allowed
