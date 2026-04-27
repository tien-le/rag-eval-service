"""Validate test environment before running tests."""

import os
import sys
from pathlib import Path

# Add project root to Python path to allow imports
# This allows the script to be run from any directory
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# pylint: disable=C0415
from app.core.logging import get_logger, setup_logging  # noqa

# Setup logging
setup_logging()
logger = get_logger(__name__)


def validate_test_environment() -> None:
    """
    Validate that test environment is properly configured.

    Raises:
        SystemExit: If test environment validation fails
    """
    logger.info("Validating test environment...")

    # Ensure APP_ENV is set to test
    app_env = os.environ.get("APP_ENV", "").lower()
    if app_env != "test":
        logger.warning(
            f"APP_ENV is '{app_env}', expected 'test'. Setting APP_ENV=test",
            extra={"current_app_env": app_env},
        )
        os.environ["APP_ENV"] = "test"

    # Check if pytest is available
    try:
        import pytest

        logger.info(f"pytest version: {pytest.__version__}")
    except ImportError:
        logger.error("pytest is not installed. Please install test dependencies.")
        sys.exit(1)

    # Check if test directory exists
    test_dir = Path("tests")
    if not test_dir.exists():
        logger.warning("Tests directory not found", extra={"test_dir": str(test_dir)})
    else:
        logger.info("Tests directory found", extra={"test_dir": str(test_dir)})

    # Validate required test environment variables
    required_vars = {
        "SECRET_KEY": os.environ.get("SECRET_KEY"),
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
    }

    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        logger.warning(
            "Some test environment variables are not set, using defaults",
            extra={"missing_vars": missing_vars},
        )
        # Set defaults for tests if not provided
        if "SECRET_KEY" not in os.environ:
            os.environ["SECRET_KEY"] = (
                "test-secret-key-for-testing-purposes-only-min-32-chars"
            )
        if "JWT_SECRET_KEY" not in os.environ:
            os.environ["JWT_SECRET_KEY"] = (
                "test-jwt-secret-key-for-testing-purposes-only-min-32-chars"
            )

    logger.info("Test environment validation completed successfully")


def main() -> None:
    """Main entry point for the script."""
    validate_test_environment()


if __name__ == "__main__":
    main()
