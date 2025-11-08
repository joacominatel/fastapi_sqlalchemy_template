from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import healthcheck, users
from core.config import settings
from core.logging import logger, setup_logging
from db.session import init_models


def create_app() -> FastAPI:
    """Factory pattern: creates and configures a FastAPI application."""
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

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    app.include_router(healthcheck, prefix=f"{settings.API_PREFIX}")
    app.include_router(users, prefix=f"{settings.API_PREFIX}")

    return app
