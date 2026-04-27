from typing import Any, Generic, TypeVar
from collections.abc import Sequence

from sqlalchemy import asc, desc, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id_: int) -> ModelType | None:
        return await self.session.get(self.model, id_)

    async def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: Any | None = None,
        descending: bool = False,
    ) -> Sequence[ModelType]:
        limit = min(max(limit, 1), 500)

        stmt = select(self.model)

        if order_by is not None:
            stmt = stmt.order_by(desc(order_by) if descending else asc(order_by))

        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.scalars(stmt)
        return result.all()

    async def list_by_cursor(
        self,
        *,
        after_id: int | None = None,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        limit = min(max(limit, 1), 500)

        stmt = select(self.model).order_by(self.model.id).limit(limit)

        if after_id is not None:
            stmt = stmt.where(self.model.id > after_id)

        result = await self.session.scalars(stmt)
        return result.all()

    async def create(self, data: dict[str, Any]) -> ModelType:
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            if value is not None:
                setattr(instance, key, value)

        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return await self.session.scalar(stmt) or 0

    async def exists_by_id(self, id_: int) -> bool:
        stmt = select(exists().where(self.model.id == id_))
        return bool(await self.session.scalar(stmt))