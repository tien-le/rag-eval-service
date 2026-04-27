"""Create initial data in the database."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path to allow imports
# This allows the script to be run from any directory
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# pylint: disable=C0415
from sqlalchemy.ext.asyncio import AsyncSession  # noqa

from app.core.auth import hash_password  # noqa
from app.core.config import settings  # noqa
from app.core.logging import get_logger, setup_logging  # noqa
from app.db.repositories.user_repository import UserRepository  # noqa
from app.db.postgresql import postgresql_provider  # noqa
from app.db.sqlite import sqlite_provider  # noqa

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def init_db() -> None:
    """
    Initialize database with initial data.

    Creates a superuser if it doesn't exist.
    """
    logger.info("Initializing database with initial data")

    # Get superuser credentials from environment variables
    superuser_email = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@example.com")
    superuser_password = os.getenv("FIRST_SUPERUSER_PASSWORD", "Password123!")
    superuser_full_name = os.getenv("FIRST_SUPERUSER_FULL_NAME", "Admin User")

    try:
        # Get database session based on provider
        if settings.DB_PROVIDER.value == "sqlite":
            await sqlite_provider.connect()
            async with sqlite_provider.get_session() as session:
                await _create_superuser(
                    session, superuser_email, superuser_password, superuser_full_name
                )
        elif settings.DB_PROVIDER.value in ("supabase", "postgresql"):
            await postgresql_provider.connect()
            async with postgresql_provider.get_session() as session:
                await _create_superuser(
                    session, superuser_email, superuser_password, superuser_full_name
                )
        else:
            logger.error(f"Unsupported DB_PROVIDER: {settings.DB_PROVIDER.value}")
            sys.exit(1)

    except Exception as e:
        logger.error(
            "Failed to create initial data",
            extra={"error": str(e)},
            exc_info=True,
        )
        sys.exit(1)


async def _create_superuser(
    session: AsyncSession, email: str, password: str, full_name: str
) -> None:
    """
    Create superuser if it doesn't exist.

    Args:
        session: Database session
        email: Superuser email
        password: Superuser password
        full_name: Superuser full name
    """
    user_repo = UserRepository(session)

    # Check if superuser already exists
    existing_user = await user_repo.get_by_email(email)
    if existing_user:
        logger.info(
            "Superuser already exists, skipping creation",
            extra={"email": email},
        )
        return

    # Create superuser
    hashed_password = hash_password(password)
    superuser = await user_repo.create_user(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=True,
        confirmed=True,
    )

    # Update to superuser (need to set is_superuser flag)
    # Since create_user doesn't accept is_superuser, we'll update it after creation
    updated_superuser = await user_repo.update(
        superuser.id,
        is_superuser=True,
    )

    if updated_superuser:
        logger.info(
            "Superuser created successfully",
            extra={
                "email": email,
                "user_id": updated_superuser.id,
                "is_superuser": updated_superuser.is_superuser,
            },
        )
    else:
        logger.error(
            "Failed to update user to superuser", extra={"user_id": superuser.id}
        )
        sys.exit(1)


def main() -> None:
    """Main entry point for the script."""
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
