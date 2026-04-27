from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine_kwargs = {
    "echo": settings.DB_ECHO,
    "pool_pre_ping": True,
}

# SQLite does not support the same pooling options as PostgreSQL.
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
        }
    )

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session


"""Database session management and FastAPI dependency injection."""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.postgresql import postgresql_provider
from app.db.sqlite import sqlite_provider


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Automatically selects database based on DB_PROVIDER setting:
    - sqlite: SQLite database
    - supabase: Supabase PostgreSQL database
    - postgresql: PostgreSQL database

    Yields:
        AsyncSession instance

    Example:
        ```python
        @router.get("/users/{user_id}")
        async def get_user(
            user_id: int,
            db: Annotated[AsyncSession, Depends(get_db)]
        ):
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        ```
    """
    # Select database provider based on DB_PROVIDER setting
    if settings.DB_PROVIDER.value == "sqlite":
        async with sqlite_provider.get_session() as session:
            yield session
    elif settings.DB_PROVIDER.value in ("supabase", "postgresql"):
        async with postgresql_provider.get_session() as session:
            yield session
    else:
        raise ValueError(
            f"Unsupported DB_PROVIDER: {settings.DB_PROVIDER.value}. "
            "Supported values: supabase, postgresql, sqlite"
        )


def get_db_dependency() -> Depends:
    """
    Get database dependency based on configuration.

    Returns:
        FastAPI Depends instance for database session
    """
    return Depends(get_db)
