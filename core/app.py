from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from api.routes import healthcheck


def create_app() -> FastAPI:
    """Factory pattern: creates and configures a FastAPI application."""
    # --- Lifespan events ---
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print("Starting up...")
        yield
        print("Shutting down...")

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

    return app
