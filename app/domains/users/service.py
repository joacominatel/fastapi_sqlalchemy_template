from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry import trace

from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate, UserUpdate

class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with a duplicate identifier"""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"User with email '{email}' already exists")


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository
        self._tracer = trace.get_tracer(self.__class__.__module__)

    @classmethod
    def from_session(cls, session: AsyncSession) -> "UserService":
        return cls(UserRepository(session))

    async def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        with self._tracer.start_as_current_span(
            "UserService.list_users",
            attributes={"app.pagination.limit": limit, "app.pagination.offset": offset},
        ):
            items, total = await self._repository.list(limit=limit, offset=offset)
        return list(items), total

    async def get_user(self, user_id: UUID) -> User | None:
        with self._tracer.start_as_current_span(
            "UserService.get_user",
            attributes={"user.id": str(user_id)},
        ):
            return await self._repository.get(user_id)

    async def create_user(self, payload: UserCreate) -> User:
        with self._tracer.start_as_current_span(
            "UserService.create_user",
            attributes={"user.email": payload.email, "user.is_active": payload.is_active},
        ):
            existing = await self._repository.get_by_email(payload.email)
            if existing:
                raise UserAlreadyExistsError(payload.email)

            user = User(email=payload.email, is_active=payload.is_active)
            return await self._repository.add(user)

    async def update_user(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        attributes = {"user.id": str(user.id), "user.updates": list(data.keys())}
        with self._tracer.start_as_current_span("UserService.update_user", attributes=attributes):
            if "email" in data and data["email"] != user.email:
                existing = await self._repository.get_by_email(data["email"])
                if existing and existing.id != user.id:
                    raise UserAlreadyExistsError(data["email"])

            for field, value in data.items():
                setattr(user, field, value)

            return await self._repository.update(user)

    async def delete_user(self, user: User) -> None:
        with self._tracer.start_as_current_span(
            "UserService.delete_user",
            attributes={"user.id": str(user.id)},
        ):
            await self._repository.delete(user)
