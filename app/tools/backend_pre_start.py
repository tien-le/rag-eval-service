"""Wait for database to be ready before starting the application."""

import asyncio
import sys
from pathlib import Path
from time import sleep

# Add project root to Python path to allow imports
# This allows the script to be run from any directory
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# pylint: disable=C0415
from sqlalchemy import text  # noqa

from app.core.config import settings  # noqa
from app.core.logging import get_logger, setup_logging  # noqa
from app.db.postgresql import _postgresql_provider  # noqa
from app.db.sqlite import _sqlite_provider  # noqa

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def check_db_connection() -> bool:
    """
    Check if database connection is available.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        if settings.DB_PROVIDER.value == "sqlite":
            await _sqlite_provider.connect()
            async with _sqlite_provider.get_session() as session:
                await session.execute(text("SELECT 1"))
            logger.info("SQLite database connection successful")
            return True
        elif settings.DB_PROVIDER.value in ("supabase", "postgresql"):
            await _postgresql_provider.connect()
            async with _postgresql_provider.get_session() as session:
                await session.execute(text("SELECT 1"))
            provider_name = (
                "Supabase" if settings.DB_PROVIDER.value == "supabase" else "PostgreSQL"
            )
            logger.info(f"{provider_name} database connection successful")
            return True
        else:
            logger.error(f"Unsupported DB_PROVIDER: {settings.DB_PROVIDER.value}")
            return False
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
        return False


async def wait_for_db(max_retries: int = 30, retry_interval: int = 2) -> None:
    """
    Wait for database to be ready with retries.

    Args:
        max_retries: Maximum number of retry attempts (default: 30)
        retry_interval: Seconds between retries (default: 2)

    Raises:
        SystemExit: If database is not ready after max retries
    """
    logger.info(
        "Waiting for database to be ready",
        extra={
            "db_provider": settings.DB_PROVIDER.value,
            "max_retries": max_retries,
            "retry_interval": retry_interval,
        },
    )

    for attempt in range(1, max_retries + 1):
        if await check_db_connection():
            logger.info("Database is ready")
            return

        logger.warning(
            f"Database not ready, retrying ({attempt}/{max_retries})...",
            extra={"attempt": attempt, "max_retries": max_retries},
        )
        sleep(retry_interval)

    logger.error(
        "Database connection failed after maximum retries",
        extra={"max_retries": max_retries},
    )
    sys.exit(1)


def main() -> None:
    """Main entry point for the script."""
    asyncio.run(wait_for_db())


if __name__ == "__main__":
    main()
