from __future__ import annotations

"""OpenTelemetry bootstrap helpers

Extend :func:`configure_tracing` to wire exporters, resources, and FastAPI
instrumentation when observability requirements mature
"""

from typing import TYPE_CHECKING, Awaitable, Callable

from app.core.config import AppBaseSettings, settings as global_settings

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.sdk.trace.export import SpanExporter
    from sqlalchemy.ext.asyncio import AsyncEngine

_TRACER_CONFIGURED = False
_INSTRUMENTED_APPS: set[int] = set()


def configure_tracing(
    *,
    exporter: "SpanExporter | None" = None,
    service_name: str | None = None,
    settings: AppBaseSettings | None = None,
) -> Callable[[], None] | None:
    """Configure the global tracer provider and return a shutdown hook.

    The function is idempotent: subsequent calls reuse the existing provider.
    """

    from opentelemetry import propagate, trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.semconv.attributes.service_attributes import SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.baggage.propagation import W3CBaggagePropagator

    global _TRACER_CONFIGURED
    if _TRACER_CONFIGURED:
        return lambda: None

    cfg = settings or global_settings
    if not cfg.TRACING_ENABLED:
        return None

    dataset = cfg.AXIOM_TRACES_DATASET_NAME or cfg.AXIOM_DATASET_NAME
    api_key = cfg.AXIOM_API_KEY.strip()
    if not api_key:
        raise RuntimeError("Tracing enabled but AXIOM_API_KEY is missing")

    resource = Resource.create(
        {
            SERVICE_NAME: service_name or cfg.APP_NAME,
            SERVICE_VERSION: cfg.VERSION,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: cfg.ENVIRONMENT,
        }
    )

    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(cfg.TRACING_SAMPLE_RATIO)),
    )

    if exporter is None:
        exporter = OTLPSpanExporter(
            endpoint=str(cfg.AXIOM_OTLP_ENDPOINT),
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Axiom-Dataset": dataset,
            },
            timeout=cfg.AXIOM_REQUEST_TIMEOUT_SECONDS,
        )

    assert exporter is not None

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    from opentelemetry.propagators.composite import CompositePropagator

    propagate.set_global_textmap(CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()]))

    _TRACER_CONFIGURED = True

    def _shutdown() -> None:
        global _TRACER_CONFIGURED
        provider.shutdown()
        _TRACER_CONFIGURED = False

    return _shutdown


def _instrument_fastapi(app: "FastAPI") -> Callable[[], None]:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    if id(app) in _INSTRUMENTED_APPS:
        return lambda: None

    FastAPIInstrumentor.instrument_app(app)
    _INSTRUMENTED_APPS.add(id(app))

    def _uninstrument() -> None:
        try:
            FastAPIInstrumentor.uninstrument_app(app)
        finally:
            _INSTRUMENTED_APPS.discard(id(app))

    return _uninstrument


def _instrument_sqlalchemy(engine: "AsyncEngine | None") -> Callable[[], None]:
    if engine is None:
        return lambda: None

    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    instrumentor = SQLAlchemyInstrumentor()
    instrumentor.instrument(engine=engine.sync_engine)

    def _uninstrument() -> None:
        instrumentor.uninstrument()

    return _uninstrument


def _instrument_httpx() -> Callable[[], None]:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    instrumentor = HTTPXClientInstrumentor()
    instrumentor.instrument()

    def _uninstrument() -> None:
        instrumentor.uninstrument()

    return _uninstrument


class ObservabilityController:
    """Coordinates telemetry setup across the application."""

    def __init__(self, settings: AppBaseSettings, *, engine: "AsyncEngine | None" = None) -> None:
        self._settings = settings
        self._engine = engine
        self._shutdown_callbacks: list[Callable[[], None] | Callable[[], Awaitable[None]]] = []
        self._configured = False

    def startup(self, app: "FastAPI | None" = None) -> None:
        if self._configured or not self._settings.TRACING_ENABLED:
            return

        shutdown = configure_tracing(settings=self._settings)
        if shutdown:
            self._shutdown_callbacks.append(shutdown)

        if app is not None:
            self._shutdown_callbacks.append(_instrument_fastapi(app))

        self._shutdown_callbacks.append(_instrument_httpx())

        if self._engine is not None:
            self._shutdown_callbacks.append(_instrument_sqlalchemy(self._engine))

        self._configured = True

    async def shutdown(self) -> None:
        import inspect
        import sys

        while self._shutdown_callbacks:
            callback = self._shutdown_callbacks.pop()
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # pragma: no cover - defensive logging
                sys.stderr.write(f"Observability shutdown error: {exc}\n")

        self._configured = False


__all__ = ["configure_tracing", "ObservabilityController"]