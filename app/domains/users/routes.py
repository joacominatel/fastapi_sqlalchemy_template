from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import get_user_service
from app.core.logging import logger
from app.domains.users.schemas import UserCollection, UserCreate, UserRead, UserUpdate
from app.domains.users.service import UserAlreadyExistsError, UserService

router = APIRouter(prefix="/users", tags=["users"])

async def _get_user_or_404(service: UserService, user_id: UUID):
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=UserCollection)
async def list_users_endpoint(
    service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of users to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of users to skip before collecting results")] = 0,
) -> UserCollection:
    items, total = await service.list_users(limit=limit, offset=offset)
    logger.bind(limit=limit, offset=offset).debug("Fetched users page")
    payload = [UserRead.model_validate(item) for item in items]
    return UserCollection(items=payload, total=total, limit=limit, offset=offset)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    try:
        user = await service.create_user(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user_endpoint(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = await _get_user_or_404(service, user_id)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: UUID,
    payload: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = await _get_user_or_404(service, user_id)
    if not payload.model_dump(exclude_unset=True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    try:
        updated = await service.update_user(user, payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from exc

    return UserRead.model_validate(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> Response:
    user = await _get_user_or_404(service, user_id)
    await service.delete_user(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
