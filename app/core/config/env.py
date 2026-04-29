"""Environment configuration loader."""

import os
from enum import Enum
from pathlib import Path
from typing import Any


class Environment(str, Enum):
    """Application environments."""

    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PREPROD = "preprod"
    PROD = "prod"


def get_environment() -> Environment:
    """Get current environment from ENV variable."""
    env = os.getenv("ENVIRONMENT", "dev").lower()
    try:
        return Environment(env)
    except ValueError:
        return Environment.DEV


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == Environment.PROD


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == Environment.DEV


def load_env_file(env: Environment | None = None) -> None:
    """Load environment file if python-dotenv is available.

    Args:
        env: Environment to load. If None, uses current environment.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env = env or get_environment()
    project_root = Path(__file__).parent.parent.parent.parent

    env_files = [
        project_root / f"configs/env/{env.value}.env",
        project_root / f".env.{env.value}",
        project_root / ".env",
    ]

    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=True)
            break


def get_env_var(key: str, default: Any = None, required: bool = False) -> Any:
    """Get environment variable with optional default and required check.

    Args:
        key: Environment variable name
        default: Default value if not set
        required: If True, raises ValueError when not set

    Returns:
        Environment variable value or default

    Raises:
        ValueError: If required=True and variable is not set
    """
    value = os.getenv(key)
    if value is None:
        if required:
            raise ValueError(f"Required environment variable {key} is not set")
        return default
    return value


def get_bool_env(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    value = os.getenv(key, str(default).lower())
    return value.lower() in ("true", "1", "yes", "on")


def get_int_env(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_list_env(key: str, default: list[str] | None = None, separator: str = ",") -> list[str]:
    """Get list environment variable (comma-separated by default)."""
    value = os.getenv(key)
    if value is None:
        return default or []
    return [v.strip() for v in value.split(separator) if v.strip()]
