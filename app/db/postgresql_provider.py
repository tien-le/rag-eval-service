"""PostgreSQL database connection with SQLAlchemy 2.0 async support."""

from collections.abc import AsyncGenerator
from typing import AsyncContextManager
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.db.database_provider import DatabaseProvider


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class PostgreSQLProvider(DatabaseProvider):
    """
    PostgreSQL database provider implementing DatabaseProvider interface.

    Manages PostgreSQL connection pool and session factory.
    """

    def __init__(self) -> None:
        """Initialize PostgreSQL provider."""
        self.engine: AsyncEngine | None = None
        self.async_session_maker: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        """Establish PostgreSQL database connection."""
        if self.engine is None:
            database_url = self._get_database_url()
            self.engine = create_async_engine(
                database_url,
                echo=settings.DEBUG_MODE,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=3600,
                future=True,
            )
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

    async def disconnect(self) -> None:
        """Close PostgreSQL database connection."""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.async_session_maker = None

    @asynccontextmanager
    async def get_session(self) -> AsyncContextManager[AsyncSession]:
        """
        Get database session context manager.

        Yields:
            AsyncSession instance
        """
        if self.async_session_maker is None:
            await self.connect()

        if self.async_session_maker is None:
            raise RuntimeError("Database session factory not initialized")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @staticmethod
    def _get_database_url() -> str:
        """
        Get database URL, ensuring asyncpg driver for PostgreSQL.

        Uses SUPABASE_DB_URL when DB_PROVIDER is supabase, otherwise uses DATABASE_URL.

        Returns:
            Database URL with asyncpg driver
        """
        # Use Supabase DB URL if provider is Supabase and URL is configured
        if settings.DB_PROVIDER.value == "supabase" and settings.SUPABASE_DB_URL:
            url = settings.SUPABASE_DB_URL
        elif settings.DATABASE_URL:
            url = settings.DATABASE_URL
        else:
            raise ValueError(
                "DATABASE_URL or SUPABASE_DB_URL must be configured. "
                f"Current DB_PROVIDER: {settings.DB_PROVIDER.value}"
            )

        # Ensure asyncpg driver for PostgreSQL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)

        return url


# Global PostgreSQL provider instance
_postgresql_provider = PostgreSQLProvider()

# Backward compatibility: expose engine and session_maker
# These will be set when provider connects
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """
    Initialize database engine and session factory.

    Note: This is a synchronous wrapper for backward compatibility.
    For new code, use `await _postgresql_provider.connect()` directly.
    """
    # This will be called async in lifespan, but we maintain sync interface
    # for backward compatibility. The actual connection happens in connect()
    pass


async def close_db() -> None:
    """Close database engine and connections."""
    await _postgresql_provider.disconnect()
    # Update global references
    global engine, async_session_maker
    engine = None
    async_session_maker = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session context manager.

    Yields:
        AsyncSession instance

    Example:
        ```python
        async with get_db_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
        ```
    """
    async with _postgresql_provider.get_session() as session:
        # Update global references for backward compatibility
        global engine, async_session_maker
        engine = _postgresql_provider.engine
        async_session_maker = _postgresql_provider.async_session_maker
        yield session


async def enable_pgvector() -> None:
    """
    Enable pgvector extension in PostgreSQL for vector operations.

    This should be called during application startup if vector
    operations are needed.
    """
    if _postgresql_provider.engine is None:
        await _postgresql_provider.connect()

    if _postgresql_provider.engine is None:
        raise RuntimeError("Database engine not initialized")

    async with _postgresql_provider.engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


# Note: Database initialization is lazy - it happens automatically when
# get_db_session() or get_db() is first called. This allows:
# - Development: No connection errors if DB isn't running at import time
# - Testing: Explicit control via fixtures
# - Production: Initialization happens on first request (or can be done
#   explicitly in application startup lifespan via _postgresql_provider.connect())
