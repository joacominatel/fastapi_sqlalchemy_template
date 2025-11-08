# FastAPI + SQLAlchemy Async Template (2025 Edition)

> A modern, no-nonsense template for building scalable FastAPI backends with async SQLAlchemy, Alembic, and `uv` as the package manager.  
> Built with mate by [joacominatel](https://jminatel.dev/) 🧉

---

## Why this exists

Because every time you want to start a new FastAPI project, you waste an hour repeating the same boring setup:  
creating the venv, installing dependencies, wiring the DB, configuring Alembic, copying `.env` samples, etc.

This repo gives you a clean, up-to-date, async-ready structure that you can clone and start coding immediately.  
No hacks, no tutorial boilerplate, no half-baked “example_app.py”s. Just a good foundation.

---

## Tech stack
* `uv`: using `Python 3.14`
* **Postgres**: In `docker-compose.yml` version `18-alpine`
* **FastAPI**
* **Alembic** for migrations
* **Async SQL Alchemy**
* **Prometheus metrics** via `prometheus-fastapi-instrumentator`
* **pytest + httpx** for async testing
