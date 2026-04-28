# Use Alembic in production. This is useful for local/dev only.
# ============================================================

from app.db.base import Base
from app.db.session import engine


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
