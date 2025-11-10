.PHONY: dev test coverage lint format migrate down

help:
	@echo "Available commands:"
	@echo "  make dev        - Run the FastAPI development server"
	@echo "  make test       - Run tests with pytest"
	@echo "  make coverage   - Run tests with coverage report"
	@echo "  make lint       - Lint the codebase with ruff"
	@echo "  make format     - Format the codebase with black"
	@echo "  make migrate    - Create and apply database migrations"
	@echo "  make down       - Stop and remove Docker containers and volumes"

dev:
	uv run fastapi dev app/main.py

test:
	uv run pytest -v

coverage:
	uv run pytest --cov=app --cov-report=term-missing --asyncio-mode=auto

lint:
	uv run ruff check .

format:
	uv run black .

migrate:
	uv run alembic revision --autogenerate -m "$(m)"
	uv run alembic upgrade head

down:
	docker compose down -v