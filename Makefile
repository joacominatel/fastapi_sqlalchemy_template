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