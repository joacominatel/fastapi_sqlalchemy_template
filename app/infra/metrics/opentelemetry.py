from __future__ import annotations

"""OpenTelemetry bootstrap helpers

Extend :func:`configure_tracing` to wire exporters, resources, and FastAPI
instrumentation when observability requirements mature
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing helper only
    from opentelemetry.sdk.trace.export import SpanExporter


def configure_tracing(*, exporter: "SpanExporter | None" = None, service_name: str = "fastapi-template") -> None:
    """Set up a minimal tracer provider.

    The function is intentionally lightweight to keep runtime costs at zero when
    tracing is not required. Provide a "SpanExporter" implementation to send
    spans to backend
    """
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if exporter is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)


__all__ = ["configure_tracing"]