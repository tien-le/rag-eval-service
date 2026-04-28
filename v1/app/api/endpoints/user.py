from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_user_service
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: UserService = Depends(get_user_service),
):
    return await service.list_users(limit=limit, offset=offset)


@router.get("/cursor", response_model=list[UserRead])
async def list_users_by_cursor(
    after_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    service: UserService = Depends(get_user_service),
):
    return await service.list_users_by_cursor(after_id=after_id, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    return await service.get_user(user_id)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return await service.create_user(payload)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    return await service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    await service.delete_user(user_id)
