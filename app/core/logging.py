from __future__ import annotations

import logging
import os
import socket
import sys
from typing import Final
from loguru import logger as _logger
from app.core.config import settings
from app.core.dependencies import (
    method_ctx,
    path_ctx,
    request_id_ctx,
    trace_id_ctx,
    user_id_ctx,
)

_LOGGER_CONFIGURED: bool = False

_STATIC_EXTRA: Final = {
    "app": settings.APP_NAME,
    "environment": settings.ENVIRONMENT,
    "version": settings.VERSION,
    "host": socket.gethostname(),
    "pid": os.getpid(),
}

_LOGGER_NAMES_TO_INTERCEPT: Final = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "uvicorn.asgi",
    "sqlalchemy",
)

class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:  # check for logging module file
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _setup_stdlib_logging(level: int) -> None:
    handler = InterceptHandler()  # custom handler to route stdlib logs to loguru
    logging.basicConfig(handlers=[handler], level=level, force=True)

    for name in _LOGGER_NAMES_TO_INTERCEPT:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [handler]
        std_logger.propagate = False
        std_logger.setLevel(level)


def _patch_record(record: dict) -> None:
    """Inject request context into every log record"""
    context = {
        "request_id": request_id_ctx.get(),
        "trace_id": trace_id_ctx.get(),
        "path": path_ctx.get(),
        "method": method_ctx.get(),
        "user_id": user_id_ctx.get(),
    }
    filtered = {k: v for k, v in context.items() if v}
    if filtered:
        record.setdefault("extra", {}).update(filtered)


def setup_logging() -> None:
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    _logger.remove()
    _logger.configure(extra=_STATIC_EXTRA, patcher=_patch_record)  # type: ignore[arg-type]

    _logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL.upper(),
        serialize=True,
        enqueue=True,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
    )

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    _setup_stdlib_logging(level)

    _LOGGER_CONFIGURED = True


def reset_request_context() -> None:
    request_id_ctx.set(None)
    trace_id_ctx.set(None)
    path_ctx.set(None)
    method_ctx.set(None)
    user_id_ctx.set(None)


def update_request_context(**kwargs: object) -> None:
    if "request_id" in kwargs:
        request_id_ctx.set(str(kwargs["request_id"]))
    if "trace_id" in kwargs:
        trace_id_ctx.set(str(kwargs["trace_id"]))
    if "path" in kwargs:
        path_ctx.set(str(kwargs["path"]))
    if "method" in kwargs:
        method_ctx.set(str(kwargs["method"]))
    if "user_id" in kwargs:
        value = kwargs["user_id"]
        user_id_ctx.set(None if value is None else str(value))


def get_request_context() -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "request_id": request_id_ctx.get(),
            "trace_id": trace_id_ctx.get(),
            "path": path_ctx.get(),
            "method": method_ctx.get(),
            "user_id": user_id_ctx.get(),
        }.items()
        if value
    }


logger = _logger

__all__ = ["logger", "setup_logging", "update_request_context", "reset_request_context", "get_request_context"]
