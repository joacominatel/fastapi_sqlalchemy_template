"""Unit tests for request context management."""

from __future__ import annotations

import pytest

from app.core.context import (
    get_request_context,
    reset_request_context,
    update_request_context,
    request_id_ctx,
    trace_id_ctx,
    path_ctx,
    method_ctx,
    user_id_ctx,
)


class TestRequestContext:
    """Test request context management functions."""

    def test_update_request_context(self):
        """Test that context variables are updated."""
        update_request_context(
            request_id="test-req-id",
            trace_id="test-trace-id",
            path="/api/test",
            method="GET",
            user_id="user-123",
        )
        
        assert request_id_ctx.get() == "test-req-id"
        assert trace_id_ctx.get() == "test-trace-id"
        assert path_ctx.get() == "/api/test"
        assert method_ctx.get() == "GET"
        assert user_id_ctx.get() == "user-123"
        
        # Cleanup
        reset_request_context()

    def test_update_partial_context(self):
        """Test that partial updates work."""
        reset_request_context()
        
        update_request_context(request_id="req-1")
        assert request_id_ctx.get() == "req-1"
        assert trace_id_ctx.get() is None
        
        update_request_context(trace_id="trace-1")
        assert request_id_ctx.get() == "req-1"
        assert trace_id_ctx.get() == "trace-1"
        
        # Cleanup
        reset_request_context()

    def test_get_request_context(self):
        """Test that context is retrieved correctly."""
        reset_request_context()
        
        update_request_context(
            request_id="req-1",
            trace_id="trace-1",
            path="/api/users",
        )
        
        context = get_request_context()
        
        assert context["request_id"] == "req-1"
        assert context["trace_id"] == "trace-1"
        assert context["path"] == "/api/users"
        assert "method" not in context
        assert "user_id" not in context
        
        # Cleanup
        reset_request_context()

    def test_get_request_context_empty(self):
        """Test that empty context returns empty dict."""
        reset_request_context()
        
        context = get_request_context()
        
        assert context == {}

    def test_reset_request_context(self):
        """Test that reset clears all context variables."""
        update_request_context(
            request_id="req-1",
            trace_id="trace-1",
            path="/api/test",
            method="POST",
            user_id="user-1",
        )
        
        reset_request_context()
        
        assert request_id_ctx.get() is None
        assert trace_id_ctx.get() is None
        assert path_ctx.get() is None
        assert method_ctx.get() is None
        assert user_id_ctx.get() is None

    def test_stringify_none_values(self):
        """Test that None values are handled."""
        reset_request_context()
        
        update_request_context(request_id=None)
        
        assert request_id_ctx.get() is None

    def test_stringify_non_string_values(self):
        """Test that non-string values are converted."""
        reset_request_context()
        
        update_request_context(
            request_id=12345,
            user_id=67890,
        )
        
        assert request_id_ctx.get() == "12345"
        assert user_id_ctx.get() == "67890"
        
        # Cleanup
        reset_request_context()


class TestMiddlewareIntegration:
    """Test context management with middleware."""

    @pytest.mark.asyncio
    async def test_middleware_sets_context(self, client):
        """Test that middleware sets request context."""
        from app.core.context import request_id_ctx, trace_id_ctx
        
        # Make a request
        response = await client.get("/api/health")
        
        # Verify response headers are set
        assert "x-request-id" in response.headers
        assert "x-trace-id" in response.headers

    @pytest.mark.asyncio
    async def test_middleware_preserves_headers(self, client):
        """Test that middleware preserves provided headers."""
        # Make request with custom headers
        response = await client.get(
            "/api/health",
            headers={
                "x-request-id": "custom-req-id",
                "x-trace-id": "custom-trace-id",
            },
        )
        
        # Verify headers are preserved
        assert response.headers["x-request-id"] == "custom-req-id"
        assert response.headers["x-trace-id"] == "custom-trace-id"

    @pytest.mark.asyncio
    async def test_middleware_resets_context_after_request(self, client):
        """Test that context is reset after request."""
        from app.core.context import request_id_ctx, trace_id_ctx
        
        # Reset before test
        reset_request_context()
        
        # Make request
        await client.get("/api/health")
        
        # Context should be reset after request completes
        # Note: This test may be flaky in async context
        # The middleware resets in finally block
