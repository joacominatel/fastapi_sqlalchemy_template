from __future__ import annotations

import importlib
from pathlib import Path
from pkgutil import iter_modules
from fastapi import APIRouter
from app.core.logging import logger

_DOMAINS_PACKAGE = "app.domains"

def _discover_domain_routers() -> list[APIRouter]:
    package = importlib.import_module(_DOMAINS_PACKAGE)
    package_file = getattr(package, "__file__", None)
    if not package_file:
        return []

    package_path = Path(package_file).parent
    routers: list[APIRouter] = []

    for _, module_name, is_pkg in iter_modules([str(package_path)]):
        if not is_pkg:
            continue
        module_path = f"{_DOMAINS_PACKAGE}.{module_name}.routes"
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            continue

        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            routers.append(router)
        else:
            logger.warning("Domain module '%s' missing APIRouter named 'router'", module_path)

    return routers


def build_api_router() -> APIRouter:
    api_router = APIRouter()
    for router in _discover_domain_routers():
        api_router.include_router(router)
    return api_router


__all__ = ["build_api_router"]
