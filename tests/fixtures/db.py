from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import Base, load_domain_models
from app.domains.users.models import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    load_domain_models()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="function", name="db_session_fixture")
async def db_session_fixture(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def db_session(db_session_fixture: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    yield db_session_fixture


@pytest.fixture()
def user_factory(db_session: AsyncSession) -> Callable[..., Awaitable[User]]:
    async def factory(*, email: str | None = None, is_active: bool = True) -> User:
        user = User(email=email or f"test-{uuid.uuid4()}@example.com", is_active=is_active)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return factory
