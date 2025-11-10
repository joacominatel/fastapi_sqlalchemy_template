"""Unit tests for OpenTelemetry observability integration."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from app.infra.metrics.opentelemetry import (
    ObservabilityController,
    configure_tracing,
    _instrument_fastapi,
    _instrument_httpx,
    _instrument_sqlalchemy,
)


class TestConfigureTracing:
    """Test the configure_tracing function."""

    @patch("app.infra.metrics.opentelemetry.trace")
    @patch("app.infra.metrics.opentelemetry.propagate")
    def test_configure_tracing_when_enabled(self, mock_propagate, mock_trace):
        """Test that tracing is configured when enabled."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="test-dataset",
            AXIOM_TRACES_DATASET_NAME="",
        )
        
        shutdown = configure_tracing(settings=settings)
        
        # Verify configuration was set up
        assert shutdown is not None
        assert callable(shutdown)
        assert mock_trace.set_tracer_provider.called
        assert mock_propagate.set_global_textmap.called

    def test_configure_tracing_when_disabled(self):
        """Test that tracing returns None when disabled."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=False,
        )
        
        result = configure_tracing(settings=settings)
        
        assert result is None

    def test_configure_tracing_missing_api_key(self):
        """Test that missing API key raises error."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="",
            AXIOM_DATASET_NAME="test-dataset",
        )
        
        with pytest.raises(RuntimeError, match="AXIOM_API_KEY is missing"):
            configure_tracing(settings=settings)

    def test_configure_tracing_missing_dataset(self):
        """Test that missing dataset raises error."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="",
        )
        
        with pytest.raises(RuntimeError, match="no Axiom dataset configured"):
            configure_tracing(settings=settings)

    @patch("app.infra.metrics.opentelemetry.trace")
    @patch("app.infra.metrics.opentelemetry.propagate")
    def test_configure_tracing_uses_traces_dataset(self, mock_propagate, mock_trace):
        """Test that dedicated traces dataset is used when configured."""
        from app.core.config.base import AppBaseSettings
        from unittest.mock import ANY
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="logs-dataset",
            AXIOM_TRACES_DATASET_NAME="traces-dataset",
        )
        
        with patch("app.infra.metrics.opentelemetry.OTLPSpanExporter") as mock_exporter:
            configure_tracing(settings=settings)
            
            # Verify traces dataset is used
            call_args = mock_exporter.call_args
            headers = call_args.kwargs["headers"]
            assert headers["X-Axiom-Dataset"] == "traces-dataset"

    @patch("app.infra.metrics.opentelemetry.trace")
    @patch("app.infra.metrics.opentelemetry.propagate")
    def test_configure_tracing_is_idempotent(self, mock_propagate, mock_trace):
        """Test that configure_tracing can be called multiple times."""
        from app.core.config.base import AppBaseSettings
        import app.infra.metrics.opentelemetry as otel_module
        
        # Reset the flag
        otel_module._TRACER_CONFIGURED = False
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="test-dataset",
        )
        
        # First call
        shutdown1 = configure_tracing(settings=settings)
        call_count = mock_trace.set_tracer_provider.call_count
        
        # Second call
        shutdown2 = configure_tracing(settings=settings)
        
        # Should not configure again
        assert mock_trace.set_tracer_provider.call_count == call_count
        assert shutdown2 is not None

    @patch("app.infra.metrics.opentelemetry.trace")
    @patch("app.infra.metrics.opentelemetry.propagate")
    def test_configure_tracing_with_custom_exporter(self, mock_propagate, mock_trace):
        """Test that custom exporter can be provided."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="test-dataset",
        )
        
        custom_exporter = Mock()
        
        import app.infra.metrics.opentelemetry as otel_module
        otel_module._TRACER_CONFIGURED = False
        
        shutdown = configure_tracing(settings=settings, exporter=custom_exporter)
        
        assert shutdown is not None
        assert mock_trace.set_tracer_provider.called


class TestInstrumentFastAPI:
    """Test FastAPI instrumentation."""

    @patch("app.infra.metrics.opentelemetry.FastAPIInstrumentor")
    def test_instrument_fastapi_first_time(self, mock_instrumentor_class):
        """Test that FastAPI is instrumented on first call."""
        mock_app = Mock()
        mock_instrumentor = Mock()
        mock_instrumentor_class.instrument_app = Mock()
        
        uninstrument = _instrument_fastapi(mock_app)
        
        assert callable(uninstrument)
        assert mock_instrumentor_class.instrument_app.called

    @patch("app.infra.metrics.opentelemetry.FastAPIInstrumentor")
    def test_instrument_fastapi_idempotent(self, mock_instrumentor_class):
        """Test that instrumenting same app twice is safe."""
        mock_app = Mock()
        
        # First call
        uninstrument1 = _instrument_fastapi(mock_app)
        call_count = mock_instrumentor_class.instrument_app.call_count
        
        # Second call with same app
        uninstrument2 = _instrument_fastapi(mock_app)
        
        # Should not instrument again
        assert mock_instrumentor_class.instrument_app.call_count == call_count

    @patch("app.infra.metrics.opentelemetry.FastAPIInstrumentor")
    def test_uninstrument_fastapi(self, mock_instrumentor_class):
        """Test that uninstrument cleans up properly."""
        mock_app = Mock()
        mock_instrumentor_class.uninstrument_app = Mock()
        
        uninstrument = _instrument_fastapi(mock_app)
        uninstrument()
        
        # Verify cleanup
        assert mock_instrumentor_class.uninstrument_app.called


class TestInstrumentSQLAlchemy:
    """Test SQLAlchemy instrumentation."""

    def test_instrument_sqlalchemy_with_none_engine(self):
        """Test that None engine returns no-op."""
        uninstrument = _instrument_sqlalchemy(None)
        
        assert callable(uninstrument)
        # Should be safe to call
        uninstrument()

    @patch("app.infra.metrics.opentelemetry.SQLAlchemyInstrumentor")
    def test_instrument_sqlalchemy_with_engine(self, mock_instrumentor_class):
        """Test that SQLAlchemy engine is instrumented."""
        mock_engine = Mock()
        mock_engine.sync_engine = Mock()
        mock_instrumentor = Mock()
        mock_instrumentor_class.return_value = mock_instrumentor
        
        uninstrument = _instrument_sqlalchemy(mock_engine)
        
        assert callable(uninstrument)
        assert mock_instrumentor.instrument.called

    @patch("app.infra.metrics.opentelemetry.SQLAlchemyInstrumentor")
    def test_uninstrument_sqlalchemy(self, mock_instrumentor_class):
        """Test that uninstrument cleans up SQLAlchemy."""
        mock_engine = Mock()
        mock_engine.sync_engine = Mock()
        mock_instrumentor = Mock()
        mock_instrumentor_class.return_value = mock_instrumentor
        
        uninstrument = _instrument_sqlalchemy(mock_engine)
        uninstrument()
        
        assert mock_instrumentor.uninstrument.called


class TestInstrumentHTTPX:
    """Test HTTPX instrumentation."""

    @patch("app.infra.metrics.opentelemetry.HTTPXClientInstrumentor")
    def test_instrument_httpx(self, mock_instrumentor_class):
        """Test that HTTPX client is instrumented."""
        mock_instrumentor = Mock()
        mock_instrumentor_class.return_value = mock_instrumentor
        
        uninstrument = _instrument_httpx()
        
        assert callable(uninstrument)
        assert mock_instrumentor.instrument.called

    @patch("app.infra.metrics.opentelemetry.HTTPXClientInstrumentor")
    def test_uninstrument_httpx(self, mock_instrumentor_class):
        """Test that uninstrument cleans up HTTPX."""
        mock_instrumentor = Mock()
        mock_instrumentor_class.return_value = mock_instrumentor
        
        uninstrument = _instrument_httpx()
        uninstrument()
        
        assert mock_instrumentor.uninstrument.called


class TestObservabilityController:
    """Test the ObservabilityController class."""

    def test_controller_init(self):
        """Test controller initialization."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=False,
        )
        
        controller = ObservabilityController(settings)
        
        assert controller._settings == settings
        assert controller._engine is None
        assert controller._shutdown_callbacks == []
        assert not controller._configured

    def test_startup_when_tracing_disabled(self):
        """Test that startup does nothing when tracing is disabled."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=False,
        )
        
        controller = ObservabilityController(settings)
        controller.startup()
        
        assert not controller._configured
        assert len(controller._shutdown_callbacks) == 0

    @patch("app.infra.metrics.opentelemetry.configure_tracing")
    @patch("app.infra.metrics.opentelemetry._instrument_fastapi")
    @patch("app.infra.metrics.opentelemetry._instrument_httpx")
    def test_startup_when_tracing_enabled(
        self, mock_httpx, mock_fastapi, mock_configure
    ):
        """Test that startup configures all instrumentations."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="test-dataset",
        )
        
        mock_configure.return_value = Mock()
        mock_fastapi.return_value = Mock()
        mock_httpx.return_value = Mock()
        
        controller = ObservabilityController(settings)
        mock_app = Mock()
        
        controller.startup(mock_app)
        
        assert controller._configured
        assert mock_configure.called
        assert mock_fastapi.called
        assert mock_httpx.called

    @patch("app.infra.metrics.opentelemetry.configure_tracing")
    def test_startup_is_thread_safe(self, mock_configure):
        """Test that concurrent startup calls are safe."""
        from app.core.config.base import AppBaseSettings
        import threading
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="test-dataset",
        )
        
        mock_configure.return_value = Mock()
        
        controller = ObservabilityController(settings)
        
        # Simulate concurrent calls
        threads = []
        for _ in range(5):
            t = threading.Thread(target=controller.startup)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should only configure once
        assert controller._configured
        assert mock_configure.call_count == 1

    @patch("app.infra.metrics.opentelemetry.configure_tracing")
    @patch("app.infra.metrics.opentelemetry._instrument_httpx")
    def test_startup_with_sqlalchemy_engine(self, mock_httpx, mock_configure):
        """Test startup with SQLAlchemy engine."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=True,
            AXIOM_API_KEY="test-key",
            AXIOM_DATASET_NAME="test-dataset",
        )
        
        mock_configure.return_value = Mock()
        mock_httpx.return_value = Mock()
        
        mock_engine = Mock()
        mock_engine.sync_engine = Mock()
        
        with patch("app.infra.metrics.opentelemetry._instrument_sqlalchemy") as mock_sql:
            mock_sql.return_value = Mock()
            
            controller = ObservabilityController(settings, engine=mock_engine)
            controller.startup()
            
            assert mock_sql.called

    @pytest.mark.asyncio
    async def test_shutdown_calls_all_callbacks(self):
        """Test that shutdown calls all registered callbacks."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=False,
        )
        
        controller = ObservabilityController(settings)
        
        # Add mock callbacks
        callback1 = Mock(return_value=None)
        callback2 = Mock(return_value=None)
        controller._shutdown_callbacks = [callback1, callback2]
        
        await controller.shutdown()
        
        assert callback1.called
        assert callback2.called
        assert not controller._configured

    @pytest.mark.asyncio
    async def test_shutdown_handles_async_callbacks(self):
        """Test that shutdown handles async callbacks."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=False,
        )
        
        controller = ObservabilityController(settings)
        
        # Add async callback
        async def async_callback():
            pass
        
        controller._shutdown_callbacks = [async_callback]
        
        await controller.shutdown()
        
        assert len(controller._shutdown_callbacks) == 0

    @pytest.mark.asyncio
    async def test_shutdown_handles_exceptions(self):
        """Test that shutdown continues even if callbacks raise exceptions."""
        from app.core.config.base import AppBaseSettings
        
        settings = AppBaseSettings(
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            TRACING_ENABLED=False,
        )
        
        controller = ObservabilityController(settings)
        
        # Add callback that raises
        def failing_callback():
            raise Exception("Test error")
        
        callback2 = Mock(return_value=None)
        controller._shutdown_callbacks = [failing_callback, callback2]
        
        # Should not raise
        await controller.shutdown()
        
        # Second callback should still be called
        assert callback2.called
        assert not controller._configured
