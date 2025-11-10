# AI Coding Agent Instructions

Concise, project-specific guidance for contributing to this **FastAPI + Async SQLAlchemy + DDD** template. Includes modern DevOps, observability, and automatic versioning (Hatch-VCS). Designed for scalable backend architectures with clean domain boundaries.

---

## Architecture Overview

* **Entry point:** `main.py` builds the app via `app/core/app.py:create_app()`, which wires logging, metrics, and lifecycle hooks.
* **Configuration:** `app/core/config` contains environment-specific settings (`base.py`, `dev.py`, `prod.py`).

  * Auto-detects environment via `.env` or `.env.docker`.
  * Global import: `from app.core import settings`.
  * Version auto-derived from Git tags using Hatch-VCS (`settings.VERSION`).
* **API layout:** Domain routers live in `app/domains/<domain>/routes.py` and are auto-discovered by `app/api/router.py` under the global prefix `settings.API_PREFIX`.

  * Health endpoint: `/api/health` returns app status, environment, and version.
* **Database:** Async SQLAlchemy setup in `app/db/session.py` using `AsyncSessionLocal`.

  * Models live under each domain (`app/domains/<domain>/models.py`) and inherit `app.db.base.Base`.
  * Schema bootstrap via `init_models()` (dev only) or Alembic migrations.
* **Observability:** Loguru + OpenTelemetry instrumentation.

  * Logs: JSON format with contextual metadata (`app`, `env`, `version`, `pid`, `host`).
  * Metrics: exported via Prometheus + OTLP collector (see `app/infra/metrics/opentelemetry.py`).

---

## Key Workflows

* **Start Postgres:** `docker compose up -d db`.
* **Run app (dev):** `uv run uvicorn main:app --reload`.
* **Run tests:** `make coverage` → runs pytest with async fixtures + coverage report.
* **Generate migration:**

  ```bash
  uv run alembic revision --autogenerate -m "add user table"
  uv run alembic upgrade head
  ```
* **First-time setup:** optional schema creation via `await app.db.session.init_models()` (development only).

---

## DDD Domain Structure

Each domain lives under `app/domains/<domain>/` and contains:

```
models.py       # SQLAlchemy models
schemas.py      # Pydantic contracts
repository.py   # Database access layer
service.py      # Business logic layer
routes.py       # FastAPI routes
__init__.py     # Exports domain modules for autoload
```

Keep imports **internal to the domain** unless cross-domain interaction is justified. Routers are registered automatically.

---

## Configuration & Environment

* Base settings: `app/core/config/base.py`
* Environments:

  * `DevelopmentSettings` (local/dev)
  * `ProductionSettings` (Docker/CI)
* `.env` → local, `.env.docker` → containerized.
* Settings fields can be overridden per environment.

---

## Observability & Logging

* **Loguru** provides centralized structured logging.

  * JSON logs include request metadata, timestamps, and environment context.
  * Uvicorn, SQLAlchemy, and app logs unified through `InterceptHandler`.
* **OpenTelemetry** instrumentation in `app/infra/metrics/opentelemetry.py`.

  * Exports Prometheus metrics.
  * Captures request latency, DB query time, and trace spans.
* Logs flushed asynchronously with configurable frequency (e.g., `AXIOM_LOG_FLUSH_INTERVAL_SECONDS`).

---

## Testing & CI/CD

* Tests live in `/tests` (root), separated into `unit/` and `integration/`.
* Common fixtures in `tests/conftest.py`.
* Coverage, linting, and formatting managed via `Makefile`:

  ```bash
  make coverage  # run tests + coverage
  make lint      # ruff/black checks
  make format    # apply formatting
  ```
* CI pipeline (`.github/workflows/ci.yml`) runs tests, coverage, and builds Docker images with version tagging.

---

## Automatic Versioning (Hatch-VCS)

* Version auto-derived from Git tags via Hatch-VCS.
* Integrated into settings:

  ```python
  from app.core.version import get_app_version
  VERSION: str = get_app_version()
  ```
* **Examples:**

  | State           | Output                       |
  | --------------- | ---------------------------- |
  | On tag `v1.1.0` | `1.1.0`                      |
  | On `dev` branch | `1.1.1.dev0+gHASH.dYYYYMMDD` |
* `/api/health` exposes the runtime version.
* `_version.py` generated automatically — ignored in `.gitignore`.

---

## Developer Notes

* Always write async route handlers.
* Inject DB session via `Depends(get_session)`; let context manager handle commits.
* Avoid manual engine operations — rely on sessions.
* Use timezone-aware datetimes (`DateTime(timezone=True)`).
* Keep Alembic aware of new models by ensuring domain imports in `app/db/base.py`.
* Follow semantic versioning: tag releases as `vX.Y.Z`.
* After merging `dev` → `main`, tag the release and push it.

  ```bash
  git tag v1.2.0 -m "Release 1.2.0"
  git push origin v1.2.0
  ```

---

## Gotchas & Tips

* Alembic autogenerate requires models imported before revision.
* `.env.docker` overrides `.env` when running in Docker.
* Use `DEBUG=True` to enable SQLAlchemy query echo.
* Version automatically updates per commit or tag — no manual `.env` edits.
* CI/CD uses `git describe --tags` for version tagging during builds.

---

## Safe Extensions

* Define `__all__` in domain packages to ensure imports are resolved by autoloader.
* Keep internal helpers (`util/`, `core/`, `infra/`) free of domain coupling.
* Add new domains without editing the router manually — discovery is automatic.

---

This document is self-updating with architectural changes. Extend sections as you add domains, observability providers, or infrastructure components.
