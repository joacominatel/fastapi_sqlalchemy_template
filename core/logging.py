from __future__ import annotations

import logging
import os
import socket
import sys
from typing import Final

from loguru import logger as _logger

from core.config import settings

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
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _setup_stdlib_logging(level: int) -> None:
    handler = InterceptHandler()
    logging.basicConfig(handlers=[handler], level=level, force=True)

    for name in _LOGGER_NAMES_TO_INTERCEPT:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [handler]
        std_logger.propagate = False
        std_logger.setLevel(level)


def setup_logging() -> None:
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    _logger.remove()
    _logger.configure(extra=_STATIC_EXTRA)

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


logger = _logger
