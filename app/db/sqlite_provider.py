"""SQLite database connection for development and testing."""

from collections.abc import AsyncGenerator
from typing import AsyncContextManager
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base_repository import DatabaseProvider


class SQLiteProvider(DatabaseProvider):
    """
    SQLite database provider implementing DatabaseProvider interface.

    Manages SQLite connection and session factory for development/testing.
    """

    def __init__(self) -> None:
        """Initialize SQLite provider."""
        self.engine: AsyncEngine | None = None
        self.async_session_maker: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        """Establish SQLite database connection."""
        if self.engine is None:
            self.engine = create_async_engine(
                settings.SQLITE_URL,
                echo=settings.DEBUG_MODE,
                connect_args={"check_same_thread": False},
                future=True,
            )
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

    async def disconnect(self) -> None:
        """Close SQLite database connection."""
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
            raise RuntimeError("SQLite session factory not initialized")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


def init_sqlite_db() -> None:
    """
    Initialize SQLite engine and session factory.

    Note: This is a synchronous wrapper for backward compatibility.
    For new code, use `await sqlite_provider.connect()` directly.
    """
    # This will be called async in lifespan, but we maintain sync interface
    # for backward compatibility. The actual connection happens in connect()
    pass


async def close_sqlite_db() -> None:
    """Close SQLite engine and connections."""
    await sqlite_provider.disconnect()
    # Update global references
    global sqlite_engine, sqlite_session_maker
    sqlite_engine = None
    sqlite_session_maker = None


@asynccontextmanager
async def get_sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get SQLite database session context manager.

    Yields:
        AsyncSession instance

    Example:
        ```python
        async with get_sqlite_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
        ```
    """
    async with sqlite_provider.get_session() as session:
        # Update global references for backward compatibility
        global sqlite_engine, sqlite_session_maker
        sqlite_engine = sqlite_provider.engine
        sqlite_session_maker = sqlite_provider.async_session_maker
        yield session


# Global SQLite provider instance
sqlite_provider = SQLiteProvider()

# Backward compatibility: expose engine and session_maker
sqlite_engine: AsyncEngine | None = None
sqlite_session_maker: async_sessionmaker[AsyncSession] | None = None
