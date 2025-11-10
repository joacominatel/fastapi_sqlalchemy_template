from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import socket
import sys
import threading
import time
from typing import Any, Final

import httpx
from loguru import logger as _logger

from app.core.config import settings
from app.core.context import (
    get_request_context,
    reset_request_context,
    update_request_context,
)

_LOGGER_CONFIGURED: bool = False

def _get_static_extra() -> dict[str, str | int]:
    """Get static extra fields for logging, computed once"""
    return {
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "host": socket.gethostname(),
        "pid": os.getpid(),
    }

_STATIC_EXTRA: Final = _get_static_extra()

_LOGGER_NAMES_TO_INTERCEPT: Final = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "uvicorn.asgi",
    "sqlalchemy",
)


class _AxiomLogSink:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        dataset: str,
        batch_size: int,
        flush_interval: float,
        timeout: float,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-ndjson",
            "X-Axiom-Dataset": dataset,
        }
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._timeout = timeout
        # Limit queue size to prevent unbounded memory growth (allow 40x batch size)
        self._queue: "queue.Queue[dict[str, Any] | None]" = queue.Queue(maxsize=batch_size * 40)
        self._thread = threading.Thread(target=self._drain, name="axiom-log-sink", daemon=True)
        self._thread.start()

    def __call__(self, message: "logging.LogRecord | Any") -> None:  # pragma: no cover - exercised via logging
        try:
            raw_record = message.record  # type: ignore[attr-defined]
        except AttributeError:  # fallback when receiving stdlib records
            level = getattr(message, "levelname", "INFO")
            log_time = getattr(message, "created", time.time())
            event: dict[str, Any] = {
                "_time": log_time,
                "message": getattr(message, "getMessage", lambda: str(message))(),
                "level": level,
                "logger": getattr(message, "name", "unknown"),
                "function": getattr(message, "funcName", "<unknown>"),
                "line": getattr(message, "lineno", 0),
            }
            extras: Any = {}
        else:
            level_field = raw_record.get("level")
            if hasattr(level_field, "name"):
                level_name = level_field.name
            elif isinstance(level_field, dict):
                level_name = level_field.get("name", "INFO")
            else:
                level_name = str(level_field or "INFO")

            log_time = raw_record.get("time")
            event = {
                "_time": log_time.isoformat() if hasattr(log_time, "isoformat") else log_time,
                "message": raw_record.get("message"),
                "level": level_name,
                "logger": raw_record.get("name"),
                "function": raw_record.get("function"),
                "line": raw_record.get("line"),
            }
            extras = raw_record.get("extra")

        if isinstance(extras, dict):
            event.update(extras)

        try:
            self._queue.put_nowait(event)
        except queue.Full:
            sys.stderr.write("Axiom log queue full; dropping log event\n")

    def close(self) -> None:
        try:
            self._queue.put_nowait(None)
        except queue.Full:  # pragma: no cover - rare condition
            sys.stderr.write("Axiom log queue full during shutdown; some logs may be lost\n")
        self._thread.join(timeout=self._timeout)

    def _drain(self) -> None:
        client = httpx.Client(timeout=self._timeout)
        buffer: list[dict[str, Any]] = []
        next_flush = time.monotonic() + self._flush_interval

        try:
            while True:
                timeout = max(0.0, next_flush - time.monotonic())
                try:
                    payload = self._queue.get(timeout=timeout)
                except queue.Empty:
                    if buffer:
                        self._flush_batch(client, buffer)
                        buffer.clear()
                    next_flush = time.monotonic() + self._flush_interval
                    continue
                except Exception as exc:  # pragma: no cover - catch unexpected queue errors
                    sys.stderr.write(f"Axiom log drain error: {exc}\n")
                    break

                if payload is None:
                    if buffer:
                        self._flush_batch(client, buffer)
                    break

                buffer.append(payload)
                if len(buffer) >= self._batch_size or time.monotonic() >= next_flush:
                    self._flush_batch(client, buffer)
                    buffer.clear()
                    next_flush = time.monotonic() + self._flush_interval
        finally:
            if buffer:
                self._flush_batch(client, buffer)
            client.close()

    def _flush_batch(self, client: httpx.Client, batch: list[dict[str, Any]]) -> None:
        if not batch:
            return
        ndjson = "\n".join(json.dumps(item, default=str) for item in batch)
        try:
            response = client.post(self._endpoint, content=ndjson, headers=self._headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failures are rare in tests
            sys.stderr.write(f"Failed to deliver logs to Axiom: {exc}\n")

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
    filtered = get_request_context()
    if filtered:
        record.setdefault("extra", {}).update(filtered)


def _add_axiom_sink(level: int) -> None:
    if not settings.AXIOM_LOGS_ENABLED:
        return

    api_key = settings.AXIOM_API_KEY.strip()
    dataset = settings.AXIOM_DATASET_NAME.strip()
    if not api_key or not dataset:
        sys.stderr.write("Axiom logging disabled: missing API key or dataset name\n")
        return

    base_url = str(settings.AXIOM_BASE_URL).rstrip("/")
    endpoint = f"{base_url}/v1/datasets/{dataset}/ingest"
    sink = _AxiomLogSink(
        endpoint=endpoint,
        api_key=api_key,
        dataset=dataset,
        batch_size=settings.AXIOM_LOG_BATCH_SIZE,
        flush_interval=settings.AXIOM_LOG_FLUSH_INTERVAL_SECONDS,
        timeout=settings.AXIOM_REQUEST_TIMEOUT_SECONDS,
    )
    _logger.add(sink, level=level, serialize=False, enqueue=True)
    atexit.register(sink.close)


def setup_logging() -> None:
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    _logger.remove()
    _logger.configure(extra=_STATIC_EXTRA, patcher=_patch_record)  # type: ignore[arg-type]

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_CONSOLE_ENABLED:
        _logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL.upper(),
            serialize=True,
            enqueue=True,
            backtrace=settings.DEBUG,
            diagnose=settings.DEBUG,
        )

    _setup_stdlib_logging(level)
    _add_axiom_sink(level)

    _LOGGER_CONFIGURED = True




logger = _logger

__all__ = ["logger", "setup_logging", "update_request_context", "reset_request_context", "get_request_context"]
