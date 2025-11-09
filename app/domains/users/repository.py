from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.domains.users.models import User

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, limit: int, offset: int) -> tuple[Sequence[User], int]:
        items_stmt: Select[tuple[User]] = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count(User.id))

        # Run queries sequentially; AsyncSession prohibits concurrent use
        items_result = await self._session.scalars(items_stmt)
        total_result = await self._session.scalar(count_stmt)

        items = items_result.all()
        total = int(total_result or 0)

        return items, total

    async def get(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return await self._session.scalar(stmt)

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        logger.bind(user_id=str(user.id)).info("User created")
        return user

    async def update(self, user: User) -> User:
        await self._session.commit()
        await self._session.refresh(user)
        logger.bind(user_id=str(user.id)).info("User updated")
        return user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        logger.bind(user_id=str(user.id)).info("User deleted")
