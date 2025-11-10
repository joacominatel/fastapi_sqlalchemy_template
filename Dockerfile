# =========================
# Builder stage
# =========================
FROM python:3.14-slim-trixie AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=.venv

# minimal config and packages installation, just for taking care
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# install uv
# https://docs.astral.sh/uv/guides/integration/docker/
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# install deps without dev packages
RUN uv sync --frozen --no-dev

# Copy the rest of the project
COPY . .

# Optional: compile bytecode for performance
RUN uv run python -m compileall app || true


# =========================
# Runtime stage
# =========================
FROM python:3.14-slim-trixie AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=.venv

# Create non-root user
RUN useradd -m appuser

WORKDIR /app

# Copy uv from builder
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copy resolved .venv environment
COPY --from=builder /app/.venv ./.venv

# Copy only what is necessary to run the app
COPY --from=builder /app/app ./app
COPY --from=builder /app/main.py ./main.py
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/pyproject.toml ./pyproject.toml

# here could be added other docs/configs/scripts as needed
RUN chown -R appuser:appuser /app

USER appuser

WORKDIR /app

EXPOSE 8000

# Final command: uv -> uvicorn -> main:app
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0"]