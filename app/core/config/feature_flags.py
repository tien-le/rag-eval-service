"""Feature flags configuration."""

from enum import Enum

from pydantic_settings import BaseSettings


class FeatureFlag(str, Enum):
    """Feature flags for gradual rollouts."""

    # Workflow features
    WORKFLOW_V2 = "workflow_v2"
    LANGGRAPH_RUNTIME = "langgraph_runtime"
    CONDITIONAL_EDGES = "conditional_edges"

    # Evaluation features
    RAGAS_MULTI_TURN = "ragas_multi_turn"
    AGENT_EVALUATION = "agent_evaluation"
    PROMPT_EVALUATION = "prompt_evaluation"

    # Infrastructure features
    KAFKA_EVENTS = "kafka_events"
    SEMANTIC_CACHE = "semantic_cache"
    DISTRIBUTED_LOCKS = "distributed_locks"

    # Security features
    ENHANCED_AUDIT = "enhanced_audit"
    PII_DETECTION = "pii_detection"
    PROMPT_INJECTION_GUARD = "prompt_injection_guard"


class FeatureFlags(BaseSettings):
    """Feature flag configuration with environment-based defaults."""

    # Default feature states (comma-separated list of enabled features)
    ENABLED_FEATURES: str = ""

    # Feature flag refresh interval (seconds)
    FEATURE_FLAGS_REFRESH_INTERVAL: int = 60

    # Feature flag store (redis, database, or env)
    FEATURE_FLAGS_STORE: str = "env"

    # Redis key for feature flags (if using redis)
    FEATURE_FLAGS_REDIS_KEY: str = "feature_flags"

    class Config:
        env_file_encoding = "utf-8"
        case_sensitive = True

    def _get_enabled_set(self) -> set[str]:
        """Get set of enabled feature flag names."""
        return {f.strip() for f in self.ENABLED_FEATURES.split(",") if f.strip()}

    def is_enabled(self, flag: FeatureFlag | str) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag: Feature flag to check

        Returns:
            True if feature is enabled
        """
        flag_name = flag.value if isinstance(flag, FeatureFlag) else flag
        enabled = self._get_enabled_set()

        # Check for wildcard or specific flag
        return "*" in enabled or flag_name in enabled

    def enable(self, flag: FeatureFlag | str) -> None:
        """Enable a feature flag (in-memory only)."""
        flag_name = flag.value if isinstance(flag, FeatureFlag) else flag
        enabled = self._get_enabled_set()
        enabled.add(flag_name)
        self.ENABLED_FEATURES = ",".join(enabled)

    def disable(self, flag: FeatureFlag | str) -> None:
        """Disable a feature flag (in-memory only)."""
        flag_name = flag.value if isinstance(flag, FeatureFlag) else flag
        enabled = self._get_enabled_set()
        enabled.discard(flag_name)
        self.ENABLED_FEATURES = ",".join(enabled)

    def get_all_flags(self) -> dict[str, bool]:
        """Get state of all known feature flags."""
        enabled = self._get_enabled_set()
        return {
            flag.value: flag.value in enabled or "*" in enabled for flag in FeatureFlag
        }


# Global feature flags instance
_feature_flags: FeatureFlags | None = None


def get_feature_flags() -> FeatureFlags:
    """Get feature flags singleton."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags


def is_feature_enabled(flag: FeatureFlag | str) -> bool:
    """Convenience function to check if a feature is enabled."""
    return get_feature_flags().is_enabled(flag)
