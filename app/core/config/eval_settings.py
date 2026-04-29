"""Evaluation settings configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class EvalSettings(BaseSettings):
    """RAG evaluation and quality gate settings."""

    # Default quality gate thresholds
    DEFAULT_FAITHFULNESS_THRESHOLD: float = Field(default=0.85, ge=0, le=1)
    DEFAULT_ANSWER_RELEVANCY_THRESHOLD: float = Field(default=0.80, ge=0, le=1)
    DEFAULT_CONTEXT_PRECISION_THRESHOLD: float = Field(default=0.75, ge=0, le=1)
    DEFAULT_CONTEXT_RECALL_THRESHOLD: float = Field(default=0.75, ge=0, le=1)
    DEFAULT_CONTEXT_RELEVANCE_THRESHOLD: float = Field(default=0.70, ge=0, le=1)

    # Evaluation execution settings
    EVAL_DEFAULT_TIMEOUT: int = Field(default=300, ge=30, le=3600)
    EVAL_MAX_CONCURRENT: int = Field(default=10, ge=1, le=50)
    EVAL_BATCH_SIZE: int = Field(default=100, ge=10, le=1000)

    # Ragas-specific settings
    RAGAS_EMBEDDING_MODEL: str = "text-embedding-3-small"
    RAGAS_LLM_MODEL: str = "gpt-4o-mini"
    RAGAS_TEMPERATURE: float = Field(default=0.0, ge=0, le=2)

    # Offline evaluation settings
    OFFLINE_EVAL_DATASET_PATH: str | None = None
    OFFLINE_EVAL_OUTPUT_PATH: str = "./eval_results"
    OFFLINE_EVAL_SAVE_INTERMEDIATE: bool = True

    # Online evaluation (production sampling)
    ONLINE_EVAL_ENABLED: bool = False
    ONLINE_EVAL_SAMPLE_RATE: float = Field(default=0.01, ge=0, le=1)  # 1% of traffic
    ONLINE_EVAL_MIN_SAMPLES: int = Field(default=10, ge=1)

    # Regression testing
    REGRESSION_TEST_ENABLED: bool = True
    REGRESSION_TEST_DATASET: str | None = None
    REGRESSION_THRESHOLD_DELTA: float = Field(default=0.05, ge=0, le=0.5)  # Max 5% regression

    # Metric catalog
    METRIC_CATALOG_PATH: str | None = None  # Path to custom metric definitions

    class Config:
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_quality_gate_thresholds(self) -> dict[str, float]:
        """Get default quality gate thresholds."""
        return {
            "faithfulness": self.DEFAULT_FAITHFULNESS_THRESHOLD,
            "answer_relevancy": self.DEFAULT_ANSWER_RELEVANCY_THRESHOLD,
            "context_precision": self.DEFAULT_CONTEXT_PRECISION_THRESHOLD,
            "context_recall": self.DEFAULT_CONTEXT_RECALL_THRESHOLD,
            "context_relevance": self.DEFAULT_CONTEXT_RELEVANCE_THRESHOLD,
        }
