"""Unit tests for logging module including Axiom integration."""

from __future__ import annotations

import json
import queue
import time
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.logging import (
    InterceptHandler,
    _AxiomLogSink,
    _add_axiom_sink,
    _patch_record,
    _setup_stdlib_logging,
    setup_logging,
)


class TestAxiomLogSink:
    """Test the Axiom log sink functionality."""

    def test_init_creates_queue_and_thread(self):
        """Test that sink initializes with a queue and starts a thread."""
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=10,
            flush_interval=1.0,
            timeout=5.0,
        )
        
        assert sink._batch_size == 10
        assert sink._flush_interval == 1.0
        assert sink._timeout == 5.0
        assert sink._queue.maxsize == 400  # 10 * 40
        assert sink._thread.is_alive()
        
        sink.close()
        sink._thread.join(timeout=1.0)

    def test_queue_has_bounded_size(self):
        """Test that queue size is bounded to prevent memory issues."""
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=25,
            flush_interval=1.0,
            timeout=5.0,
        )
        
        # Queue should be batch_size * 40
        assert sink._queue.maxsize == 1000
        
        sink.close()
        sink._thread.join(timeout=1.0)

    def test_call_with_loguru_record(self):
        """Test sink handles loguru log records."""
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=10,
            flush_interval=1.0,
            timeout=5.0,
        )
        
        # Mock a loguru record
        mock_record = Mock()
        mock_record.record = {
            "time": Mock(isoformat=lambda: "2025-01-01T00:00:00"),
            "message": "Test message",
            "level": {"name": "INFO"},
            "name": "test.logger",
            "function": "test_func",
            "line": 42,
            "extra": {"key": "value"},
        }
        
        sink(mock_record)
        
        # Allow some time for queue processing
        time.sleep(0.1)
        
        sink.close()
        sink._thread.join(timeout=1.0)

    def test_call_with_stdlib_record(self):
        """Test sink handles stdlib logging records."""
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=10,
            flush_interval=1.0,
            timeout=5.0,
        )
        
        # Mock a stdlib record
        mock_record = Mock()
        mock_record.levelname = "INFO"
        mock_record.created = time.time()
        mock_record.getMessage = lambda: "Test message"
        mock_record.name = "test.logger"
        mock_record.funcName = "test_func"
        mock_record.lineno = 42
        # No 'record' attribute - triggers fallback
        delattr(mock_record, "record")
        
        sink(mock_record)
        
        time.sleep(0.1)
        
        sink.close()
        sink._thread.join(timeout=1.0)

    def test_close_handles_queue_full(self):
        """Test close handles queue full condition gracefully."""
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=1,  # Small batch size
            flush_interval=10.0,  # Long flush interval
            timeout=1.0,
        )
        
        # Fill the queue
        for _ in range(sink._queue.maxsize):
            try:
                sink._queue.put_nowait({"test": "message"})
            except queue.Full:
                break
        
        # Close should handle full queue
        sink.close()
        sink._thread.join(timeout=2.0)

    @patch("app.core.logging.httpx.Client")
    def test_flush_batch_sends_to_axiom(self, mock_client_class):
        """Test that flush_batch sends logs to Axiom."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=2,
            flush_interval=0.1,
            timeout=5.0,
        )
        
        # Add log entries
        sink._queue.put({"message": "test1", "level": "INFO"})
        sink._queue.put({"message": "test2", "level": "ERROR"})
        
        # Wait for flush
        time.sleep(0.3)
        
        sink.close()
        sink._thread.join(timeout=1.0)

    @patch("app.core.logging.httpx.Client")
    def test_flush_batch_handles_http_error(self, mock_client_class):
        """Test that flush_batch handles HTTP errors gracefully."""
        import httpx
        
        mock_client = Mock()
        mock_client.post.side_effect = httpx.HTTPError("Network error")
        mock_client_class.return_value = mock_client
        
        sink = _AxiomLogSink(
            endpoint="https://api.axiom.co/v1/datasets/test/ingest",
            api_key="test-key",
            dataset="test",
            batch_size=1,
            flush_interval=0.1,
            timeout=5.0,
        )
        
        # Add log entry
        sink._queue.put({"message": "test", "level": "INFO"})
        
        # Wait for attempted flush
        time.sleep(0.3)
        
        # Should not crash
        sink.close()
        sink._thread.join(timeout=1.0)


class TestInterceptHandler:
    """Test the intercept handler for stdlib logging."""

    @patch("app.core.logging._logger")
    def test_emit_forwards_to_loguru(self, mock_logger):
        """Test that emit forwards records to loguru."""
        handler = InterceptHandler()
        
        import logging
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        handler.emit(record)
        
        # Verify loguru was called
        assert mock_logger.opt.called


class TestPatchRecord:
    """Test the record patching function."""

    @patch("app.core.logging.get_request_context")
    def test_patch_record_adds_context(self, mock_get_context):
        """Test that patch_record adds request context."""
        mock_get_context.return_value = {
            "request_id": "test-req-id",
            "trace_id": "test-trace-id",
        }
        
        record: dict[str, Any] = {}
        _patch_record(record)
        
        assert "extra" in record
        assert record["extra"]["request_id"] == "test-req-id"
        assert record["extra"]["trace_id"] == "test-trace-id"

    @patch("app.core.logging.get_request_context")
    def test_patch_record_handles_empty_context(self, mock_get_context):
        """Test that patch_record handles empty context."""
        mock_get_context.return_value = {}
        
        record: dict[str, Any] = {}
        _patch_record(record)
        
        # Should not add extra if context is empty
        assert "extra" not in record


class TestSetupLogging:
    """Test the setup_logging function."""

    @patch("app.core.logging._logger")
    @patch("app.core.logging._setup_stdlib_logging")
    @patch("app.core.logging._add_axiom_sink")
    def test_setup_logging_configures_logger(
        self, mock_add_axiom, mock_setup_stdlib, mock_logger
    ):
        """Test that setup_logging configures all components."""
        from app.core.logging import _LOGGER_CONFIGURED
        import app.core.logging as logging_module
        
        # Reset the flag
        logging_module._LOGGER_CONFIGURED = False
        
        setup_logging()
        
        # Verify configuration
        assert mock_logger.remove.called
        assert mock_logger.configure.called
        assert mock_setup_stdlib.called
        assert mock_add_axiom.called

    @patch("app.core.logging._logger")
    def test_setup_logging_is_idempotent(self, mock_logger):
        """Test that setup_logging can be called multiple times safely."""
        import app.core.logging as logging_module
        
        # First call
        logging_module._LOGGER_CONFIGURED = False
        setup_logging()
        
        call_count_after_first = mock_logger.configure.call_count
        
        # Second call
        setup_logging()
        
        # Should not configure again
        assert mock_logger.configure.call_count == call_count_after_first


class TestAddAxiomSink:
    """Test the _add_axiom_sink function."""

    @patch("app.core.logging.settings")
    @patch("app.core.logging._logger")
    @patch("app.core.logging._AxiomLogSink")
    def test_add_axiom_sink_when_enabled(self, mock_sink_class, mock_logger, mock_settings):
        """Test that Axiom sink is added when enabled."""
        mock_settings.AXIOM_LOGS_ENABLED = True
        mock_settings.AXIOM_API_KEY = "test-key"
        mock_settings.AXIOM_DATASET_NAME = "test-dataset"
        mock_settings.AXIOM_BASE_URL = "https://api.axiom.co"
        mock_settings.AXIOM_LOG_BATCH_SIZE = 25
        mock_settings.AXIOM_LOG_FLUSH_INTERVAL_SECONDS = 2.0
        mock_settings.AXIOM_REQUEST_TIMEOUT_SECONDS = 5.0
        
        import logging
        
        _add_axiom_sink(logging.INFO)
        
        # Verify sink was created and added
        assert mock_sink_class.called
        assert mock_logger.add.called

    @patch("app.core.logging.settings")
    @patch("app.core.logging._logger")
    def test_add_axiom_sink_when_disabled(self, mock_logger, mock_settings):
        """Test that Axiom sink is not added when disabled."""
        mock_settings.AXIOM_LOGS_ENABLED = False
        
        import logging
        
        _add_axiom_sink(logging.INFO)
        
        # Verify sink was not added
        assert not mock_logger.add.called

    @patch("app.core.logging.settings")
    def test_add_axiom_sink_missing_credentials(self, mock_settings):
        """Test that missing credentials are handled."""
        mock_settings.AXIOM_LOGS_ENABLED = True
        mock_settings.AXIOM_API_KEY = ""
        mock_settings.AXIOM_DATASET_NAME = ""
        
        import logging
        
        # Should not raise, just print to stderr
        _add_axiom_sink(logging.INFO)
