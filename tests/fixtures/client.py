from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.app import create_app
from app.db.session import get_session


@pytest.fixture(scope="function", name="app")
async def app_fixture(db_session: AsyncSession) -> AsyncGenerator[FastAPI, None]:
    application = create_app()

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield db_session
        finally:
            await db_session.rollback()

    application.dependency_overrides[get_session] = override_get_session
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture(scope="function", name="client_fixture")
async def client_fixture(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
async def client(client_fixture: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    yield client_fixture
