from __future__ import annotations

from collections.abc import AsyncGenerator
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base

_engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

# Add connection pooling
_db_url = str(settings.DATABASE_URL)
if "sqlite" not in _db_url.lower():
    _engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,  # Allow up to 10 additional connections when pool is exhausted
    })

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

_models_loaded = False

def _import_domain_modules(suffix: str) -> None:
    """domain submodules need to be imported so SQLAlchemy registers models"""
    package = import_module("app.domains")
    package_file = getattr(package, "__file__", None)
    if not package_file:
        return

    package_path = Path(package_file).parent

    for _, module_name, is_pkg in iter_modules([str(package_path)]):
        if not is_pkg:
            continue
        module_path = f"app.domains.{module_name}.{suffix}"
        try:
            import_module(module_path)
        except ModuleNotFoundError:
            continue


def load_domain_models() -> None:
    """Load domain models with caching to avoid repeated imports."""
    global _models_loaded
    if not _models_loaded:
        _import_domain_modules("models")
        _models_loaded = True


async def init_models() -> None:
    """
    this creates the tables from the ORM metadata
    just use it for development, not in production
    could lead to data loss...
    """
    load_domain_models()
    logger.bind(action="init_models").debug("Creating database schema from ORM metadata")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.bind(action="init_models").info("Database schema created")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            logger.exception("Database session rollback due to SQLAlchemyError")
            raise
