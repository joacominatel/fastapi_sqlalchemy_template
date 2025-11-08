# AI Coding Agent Instructions

Concise, project-specific guidance to be productive immediately in this FastAPI + Async SQLAlchemy template.

## Architecture Overview
- Entry point: `main.py` creates the app via factory `app/core/app.py:create_app()`.
- Configuration: `app/core/config` selects `DevelopmentSettings` / `ProductionSettings` via `ENVIRONMENT`. Consume globals with `from app.core import settings`.
- API layout: Domain routers live in `app/domains/<domain>/routes.py`. `app/api/router.py` discovers and aggregates routers under `settings.API_PREFIX`. Health endpoints live in `app/api/health.py`.
- Database: Async SQLAlchemy engine/session in `app/db/session.py`. Models per domain (e.g. `app/domains/users/models.py`) inherit `app.db.base.Base` naming conventions.
- Migrations: Alembic async configuration in `alembic/env.py` imports `app.db.load_domain_models()` to register metadata before autogenerate (`compare_type=True`, `compare_server_default=True`).

## Key Workflows
- Run Postgres locally: `docker compose up -d` (service `db`). Ensure `.env` has `DATABASE_URL` with async driver (e.g. `postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi_template`).
- Start server (dev): `uvicorn main:app --reload`.
- Create migration: `alembic revision --autogenerate -m "add user table"` then `alembic upgrade head`.
- First-time dev (optional schema bootstrap): call `await app.db.session.init_models()` in a one-off script; DO NOT use in production—migrations own schema.

## Adding Things
- New domain model: create `app/domains/things/models.py`:
  ```python
  from sqlalchemy import String
  from sqlalchemy.orm import Mapped, mapped_column
  from app.db.base import Base
  class Thing(Base):
      name: Mapped[str] = mapped_column(String(100), nullable=False)
  ```
  Ensure Alembic sees it: expose the model via `app/domains/things/__init__.py` and call `app.db.load_domain_models()` before `alembic revision` (already handled in env script).
- New route: `app/domains/things/routes.py`:
  ```python
  from fastapi import APIRouter, Depends
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.db.session import get_session
  router = APIRouter(prefix="/things", tags=["things"])
  @router.get("/")
  async def list_things(session: AsyncSession = Depends(get_session)):
      return []
  ```
  Export the router in `app/domains/things/__init__.py`; `app/api/router.build_api_router()` auto-includes it.
- New setting: add field to `AppBaseSettings`; override per environment in `dev.py`/`prod.py`. Reload unaffected consumers.

## Conventions & Patterns
- Always async: use `async def` route handlers and `AsyncSession` from dependency `get_session()`.
- DB sessions: inject with `Depends(get_session)`; let context manager handle commit/rollback; perform manual `await session.commit()` when mutating.
- Table & constraint naming centralized via `app/db/base.py`—avoid manual `__tablename__` unless overriding.
- Timestamps: follow pattern in `User` (`created_at` default `datetime.utcnow`, `updated_at` with `onupdate`). Keep timezone-aware (`DateTime(timezone=True)`).
- Avoid direct engine access; work through sessions unless doing migration/bootstrap tasks.

## Gotchas / Tips
- Alembic autogenerate only detects models imported before revision command; missing imports yield empty migration.
- Use `server_default` if you need Alembic to detect default changes, since `compare_server_default=True` is enabled.
- `settings.DEBUG` drives SQL echo; set `DEBUG=true` in `.env` for verbose query logging.
- Keep router prefixes consistent: routers define domain prefixes; factory applies global `settings.API_PREFIX` automatically.

## Safe Extensions
- Add `__all__` exports in `app/domains/<domain>/__init__.py` to ensure models/routers load and autogenerate sees them.
- Domain packages should co-locate schemas/services/repository so imports stay local.

Clarify or extend any section by asking (e.g. want async test pattern, error handling, or logging setup?).