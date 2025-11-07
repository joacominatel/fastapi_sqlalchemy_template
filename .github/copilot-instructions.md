# AI Coding Agent Instructions

Concise, project-specific guidance to be productive immediately in this FastAPI + Async SQLAlchemy template.

## Architecture Overview
- Entry point: `main.py` creates the app via factory `core/app.py:create_app()`.
- Configuration: `core/config.py:Settings` (pydantic-settings) loads `.env`. Add new config by extending this class; reference via `from core.config import settings`.
- API layout: Each router lives in `api/routes/<feature>.py` exposing a module-level `router`. `api/routes/__init__.py` re-exports routers; app factory includes them with global prefix `settings.API_PREFIX`.
- Database: Async SQLAlchemy engine/session in `db/session.py`. Models in `db/models/*.py` subclass `db.base.Base` which auto-generates `__tablename__` (camelCase → snake_case) and applies naming conventions for constraints.
- Migrations: Alembic configured for async in `alembic/env.py`; it injects `sqlalchemy.url` from `settings.DATABASE_URL`. Autogenerate compares types and server defaults (`compare_type=True`, `compare_server_default=True`).

## Key Workflows
- Run Postgres locally: `docker compose up -d` (service `db`). Ensure `.env` has `DATABASE_URL` with async driver (e.g. `postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi_template`).
- Start server (dev): `uvicorn main:app --reload`.
- Create migration: `alembic revision --autogenerate -m "add user table"` then `alembic upgrade head`.
- First-time dev (optional schema bootstrap): call `await db.session.init_models()` in a one-off script; DO NOT use in production—migrations own schema.

## Adding Things
- New model: create `db/models/Thing.py`:
  ```python
  from sqlalchemy import String
  from sqlalchemy.orm import Mapped, mapped_column
  from db.base import Base
  class Thing(Base):
      name: Mapped[str] = mapped_column(String(100), nullable=False)
  ```
  Ensure Alembic sees it: import the module somewhere before running `alembic revision` (e.g. add `from db.models import Thing` inside a `models/__init__.py` you create, then import that in `alembic/env.py`).
- New route: `api/routes/things.py`:
  ```python
  from fastapi import APIRouter, Depends
  from sqlalchemy.ext.asyncio import AsyncSession
  from db.session import get_session
  router = APIRouter(prefix="/things", tags=["things"])
  @router.get("/")
  async def list_things(session: AsyncSession = Depends(get_session)):
      return []
  ```
  Export in `api/routes/__init__.py` and include in `create_app()` (pattern mirrors existing healthcheck).
- New setting: add field to `Settings`; update `.env`; no manual reload needed—constructed at import time.

## Conventions & Patterns
- Always async: use `async def` route handlers and `AsyncSession` from dependency `get_session()`.
- DB sessions: inject with `Depends(get_session)`; let context manager handle commit/rollback; perform manual `await session.commit()` when mutating.
- Table & constraint naming centralized via `db/base.py`—avoid manual `__tablename__` unless overriding.
- Timestamps: follow pattern in `User` (`created_at` default `datetime.utcnow`, `updated_at` with `onupdate`). Keep timezone-aware (`DateTime(timezone=True)`).
- Avoid direct engine access; work through sessions unless doing migration/bootstrap tasks.

## Gotchas / Tips
- Alembic autogenerate only detects models imported before revision command; missing imports yield empty migration.
- Use `server_default` if you need Alembic to detect default changes, since `compare_server_default=True` is enabled.
- `settings.DEBUG` drives SQL echo; set `DEBUG=true` in `.env` for verbose query logging.
- Keep router prefixes consistent: either set in router (`APIRouter(prefix="/x")`) or rely on factory `prefix=f"{settings.API_PREFIX}"` but don’t double-prefix.

## Safe Extensions
- Add `models/__init__.py` to centralize imports (improves autogenerate reliability).
- Introduce Pydantic schemas in a `schemas/` directory for request/response contracts (not present yet).

Clarify or extend any section by asking (e.g. want async test pattern, error handling, or logging setup?).