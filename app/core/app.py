from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.health import router as health_router
from app.api.router import build_api_router
from app.core.config import settings
from app.core.logging import logger, reset_request_context, setup_logging, update_request_context
from app.db.session import init_models

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        request.state.request_id = request_id
        update_request_context(
            request_id=request_id,
            trace_id=trace_id,
            path=str(request.url.path),
            method=request.method,
        )
        logger.bind(event="request", stage="start").info("Handling request")
        try:
            response = await call_next(request)
        finally:
            reset_request_context()
        response.headers.setdefault("x-request-id", request_id)
        response.headers.setdefault("x-trace-id", trace_id)
        return response


def create_app() -> FastAPI:
    """create and configure a FASTAPI application instance"""
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.bind(event="lifespan", stage="startup").info("Application startup")
        if settings.AUTO_CREATE_SCHEMA:
            await init_models()
        yield
        logger.bind(event="lifespan", stage="shutdown").info("Application shutdown")

    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.API_PREFIX)
    app.include_router(build_api_router(), prefix=settings.API_PREFIX)

    Instrumentator(should_group_status_codes=True, should_ignore_untemplated=True).instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["metrics"],
    )

    return app
