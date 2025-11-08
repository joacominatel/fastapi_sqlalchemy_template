from __future__ import annotations

import logging
import os
import socket
import sys
from contextvars import ContextVar
from typing import Final
from loguru import logger as _logger
from app.core.config import settings

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

_REQUEST_CONTEXT: ContextVar[dict[str, str]] = ContextVar("request_context", default={})


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None: # noqa: D401
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__: # check for logging module file
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _setup_stdlib_logging(level: int) -> None:
    handler = InterceptHandler() # custom handler to route stdlib logs to loguru
    logging.basicConfig(handlers=[handler], level=level, force=True)

    for name in _LOGGER_NAMES_TO_INTERCEPT:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [handler]
        std_logger.propagate = False
        std_logger.setLevel(level)


def _patch_record(record: dict) -> None:
    """Inject request context into every log record"""
    # don't know why but if I don't put this docstring loguru complains
    context = _REQUEST_CONTEXT.get({})
    if context:
        record.setdefault("extra", {}).update(context)


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
    _REQUEST_CONTEXT.set({})


def update_request_context(**kwargs: object) -> None:
    current = _REQUEST_CONTEXT.get({}).copy()
    current.update({k: str(v) for k, v in kwargs.items() if v is not None})
    _REQUEST_CONTEXT.set(current)


def get_request_context() -> dict[str, str]:
    return _REQUEST_CONTEXT.get({}).copy()


logger = _logger

__all__ = ["logger", "setup_logging", "update_request_context", "reset_request_context", "get_request_context"]
