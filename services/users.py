from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import logger
from db.models.User import User
from schemas.user import UserCreate, UserUpdate


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with a duplicate email."""


async def list_users(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> tuple[Sequence[User], int]:
    stmt: Select[tuple[User]] = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.scalars(stmt)
    items = result.all()

    total_stmt = select(func.count(User.id))
    total = await session.scalar(total_stmt)
    return items, int(total or 0)


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return await session.scalar(stmt)


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    existing = await get_user_by_email(session, payload.email)
    if existing:
        raise UserAlreadyExistsError(payload.email)

    user = User(email=payload.email, is_active=payload.is_active)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.bind(user_id=str(user.id)).info("User created")
    return user


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != user.email:
        existing = await get_user_by_email(session, data["email"])
        if existing and existing.id != user.id:
            raise UserAlreadyExistsError(data["email"])

    for field, value in data.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    logger.bind(user_id=str(user.id)).info("User updated")
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    logger.bind(user_id=str(user.id)).info("User deleted")
