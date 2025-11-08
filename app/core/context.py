from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
path_ctx: ContextVar[str | None] = ContextVar("path", default=None)
method_ctx: ContextVar[str | None] = ContextVar("method", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def reset_request_context() -> None:
    request_id_ctx.set(None)
    trace_id_ctx.set(None)
    path_ctx.set(None)
    method_ctx.set(None)
    user_id_ctx.set(None)


def update_request_context(**kwargs: object) -> None:
    if "request_id" in kwargs:
        request_id_ctx.set(_stringify(kwargs["request_id"]))
    if "trace_id" in kwargs:
        trace_id_ctx.set(_stringify(kwargs["trace_id"]))
    if "path" in kwargs:
        path_ctx.set(_stringify(kwargs["path"]))
    if "method" in kwargs:
        method_ctx.set(_stringify(kwargs["method"]))
    if "user_id" in kwargs:
        user_id_ctx.set(_stringify(kwargs["user_id"]))


def get_request_context() -> dict[str, str]:
    context = {
        "request_id": request_id_ctx.get(),
        "trace_id": trace_id_ctx.get(),
        "path": path_ctx.get(),
        "method": method_ctx.get(),
        "user_id": user_id_ctx.get(),
    }
    return {key: value for key, value in context.items() if value}


def _stringify(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = [
    "request_id_ctx",
    "trace_id_ctx",
    "path_ctx",
    "method_ctx",
    "user_id_ctx",
    "reset_request_context",
    "update_request_context",
    "get_request_context",
]
