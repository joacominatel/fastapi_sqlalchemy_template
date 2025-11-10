# Observability Guide

This reference explains how to collect logs, traces, and metrics from the FastAPI template and forward telemetry to Axiom.

## Configuration Overview

- All observability settings live in [`app/core/config/base.py`](../app/core/config/base.py) and are controlled via environment variables.
- Key environment variables (see `.env.example`):
  - `LOG_CONSOLE_ENABLED`, `AXIOM_LOGS_ENABLED`, `AXIOM_API_KEY`, `AXIOM_DATASET`, `AXIOM_LOG_BATCH_SIZE`, `AXIOM_LOG_FLUSH_INTERVAL_SECONDS`, `AXIOM_REQUEST_TIMEOUT_SECONDS`.
  - `TRACING_ENABLED`, `TRACING_SAMPLE_RATIO`, `AXIOM_OTLP_ENDPOINT`, `AXIOM_TRACES_DATASET` (falls back to `AXIOM_DATASET` when empty).
- Restart the application after changing configuration because settings are loaded during startup.

## Logs

- **Console sink**: With `LOG_CONSOLE_ENABLED=true`, Loguru writes structured JSON to stdout for local debugging or container log aggregation.
- **Axiom sink**: Enable `AXIOM_LOGS_ENABLED=true` and provide `AXIOM_API_KEY` plus `AXIOM_DATASET` to ship logs to `https://api.axiom.co/v1/datasets/<dataset>/ingest`.
  - Batch knobs: `AXIOM_LOG_BATCH_SIZE` (default 25), `AXIOM_LOG_FLUSH_INTERVAL_SECONDS` (default 2.0), and `AXIOM_REQUEST_TIMEOUT_SECONDS` (default 5.0).
  - Each log record includes contextual fields (`request_id`, `trace_id`, `method`, `path`, `user_id` when available) and static metadata (`app`, `environment`, `version`, `host`, `pid`).
- **Header propagation**: Incoming `x-request-id` and `x-trace-id` headers are preserved; otherwise new UUIDs are generated per request. Share these headers across services to correlate events.

## Tracing

- Toggle with `TRACING_ENABLED`. When true, the `ObservabilityController` (see [`app/infra/metrics/opentelemetry.py`](../app/infra/metrics/opentelemetry.py)) performs:
  - `TracerProvider` setup using `ParentBased(TraceIdRatioBased(TRACING_SAMPLE_RATIO))` sampling.
  - OTLP HTTP export through `AXIOM_OTLP_ENDPOINT`, adding `Authorization: Bearer <AXIOM_API_KEY>` and `X-Axiom-Dataset` headers (`AXIOM_TRACES_DATASET` if provided).
  - W3C propagators (`TraceContext`, `Baggage`) registration for distributed context.
  - Auto-instrumentation of FastAPI, SQLAlchemy, and HTTPX, plus manual spans inside `app/domains/users/service.py` and `repository.py`.
- Dependencies such as `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-httpx`, and `opentelemetry-instrumentation-sqlalchemy` are already declared in `pyproject.toml`.

## Metrics

- The `GET /metrics` endpoint exposes Prometheus-compatible metrics powered by `prometheus-fastapi-instrumentator`.
- Instrumentation is configured in `app/core/app.py` (via `Instrumentator(...).instrument(app).expose(...)`).
- Sample Prometheus scrape configuration:

  ```yaml
  scrape_configs:
    - job_name: fastapi-template
      static_configs:
        - targets: ['localhost:8000']
          metrics_path: /metrics
  ```

- Exported metrics cover:
  - Request latencies and totals per route.
  - HTTP status counts (grouped by class).
  - Process statistics (memory, threads) and ASGI instrumentation data.

## End-to-End Checklist

1. Set environment variables for the target environment (development, staging, production) and restart the app.
2. Confirm logs and traces arrive in Axiom; use shared `trace_id` values for correlation.
3. Aim Prometheus, Grafana, or your preferred monitoring tool at `/metrics`.
4. Adjust `TRACING_SAMPLE_RATIO` and log batching settings according to throughput.

## Troubleshooting

- **No logs in Axiom**: Validate `AXIOM_API_KEY`, dataset name, network reachability, and that `AXIOM_LOGS_ENABLED` is true. Delivery errors are written to stderr.
- **Missing spans**: Ensure `TRACING_ENABLED=true`, instrumentation packages are installed, and the exporter credentials reference a valid dataset.
- **Propagation conflicts**: If another component sets global propagators, review `configure_tracing()` to avoid overrides or harmonize configuration across services.

Use this guide as the foundation for building dashboards and alerting tailored to your production needs.
