from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def get_user(self, user_id: int) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def list_users(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ):
        return await self.users.list(
            limit=limit,
            offset=offset,
            order_by=User.id,
        )

    async def list_users_by_cursor(
        self,
        *,
        after_id: int | None = None,
        limit: int = 100,
    ):
        return await self.users.list_by_cursor(
            after_id=after_id,
            limit=limit,
        )

    async def create_user(self, payload: UserCreate) -> User:
        async with UnitOfWork(self.session):
            existing = await self.users.get_by_email(payload.email)
            if existing:
                raise ConflictError("Email already exists")

            try:
                return await self.users.create(payload.model_dump())
            except IntegrityError as exc:
                raise ConflictError("Email already exists") from exc

    async def update_user(self, user_id: int, payload: UserUpdate) -> User:
        async with UnitOfWork(self.session):
            user = await self.users.get_by_id(user_id)
            if user is None:
                raise NotFoundError("User not found")

            data = payload.model_dump(exclude_unset=True)
            return await self.users.update(user, data)

    async def delete_user(self, user_id: int) -> None:
        async with UnitOfWork(self.session):
            user = await self.users.get_by_id(user_id)
            if user is None:
                raise NotFoundError("User not found")

            await self.users.delete(user)