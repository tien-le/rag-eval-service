"""Clear alembic_version table to fix stale revision references."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# Load config file
def load_config_file(env_name: str | None = None) -> None:
    """Load environment variables from config file."""
    if env_name is None:
        env_name = os.environ.get("APP_ENV", "dev").lower()

    if "APP_ENV" not in os.environ:
        os.environ["APP_ENV"] = env_name

    env_map = {
        "production": "prod",
        "prod": "prod",
        "staging": "staging",
        "stage": "staging",
        "test": "test",
    }
    env_file_name = env_map.get(env_name, "dev")
    config_file = project_root / "configs" / f"{env_file_name}.env"

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value


load_config_file()

# pylint: disable=C0415
from sqlalchemy import create_engine, text  # noqa
from app.core.config import settings  # noqa


def clear_alembic_version() -> None:
    """Clear the alembic_version table."""
    # Get database URL
    if settings.DB_PROVIDER.value == "supabase" and settings.SUPABASE_DB_URL:
        db_url = settings.SUPABASE_DB_URL
    elif settings.DATABASE_URL:
        db_url = settings.DATABASE_URL
    else:
        print(
            "ERROR: No database URL found. Please set DATABASE_URL or SUPABASE_DB_URL."
        )
        sys.exit(1)

    # Convert asyncpg to psycopg2 for synchronous operations
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

    # For SQLite, use synchronous driver
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

    print(
        f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}"
    )

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check if alembic_version table exists
        if "sqlite" in db_url.lower():
            result = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                )
            )
        else:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
                )
            )

        table_exists = result.scalar()

        if not table_exists:
            print("INFO: alembic_version table does not exist. Nothing to clear.")
            return

        # Get current version
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_version = result.scalar()

        if current_version:
            print(f"Current alembic version in database: {current_version}")
            print("Clearing alembic_version table...")
            conn.execute(text("DELETE FROM alembic_version"))
            conn.commit()
            print("✓ Successfully cleared alembic_version table.")
            print(
                "You can now create a new migration with: alembic revision --autogenerate -m 'initial migration'"
            )
        else:
            print("INFO: alembic_version table is empty. Nothing to clear.")


if __name__ == "__main__":
    try:
        clear_alembic_version()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
