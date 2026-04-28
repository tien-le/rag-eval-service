"""Base database provider interface for multi-database support."""

from abc import ABC, abstractmethod
from typing import AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseProvider(ABC):
    """
    Abstract base class for all database providers.

    Provides a consistent interface for database connection management
    following the Dependency Inversion Principle.

    SQLAlchemy-based providers (PostgreSQL, SQLite) should implement
    get_session() using @asynccontextmanager decorator to return an
    async context manager.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def get_session(self) -> AsyncContextManager[AsyncSession]:
        """
        Get database session context manager.

        Should be decorated with @asynccontextmanager in implementations
        to return an async context manager usable with 'async with'.

        Returns:
            AsyncContextManager that yields AsyncSession instance
        """
        pass
