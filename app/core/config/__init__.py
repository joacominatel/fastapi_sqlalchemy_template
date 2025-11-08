from __future__ import annotations

import os
from pathlib import Path
from typing import Type

from .base import AppBaseSettings
from .dev import DevelopmentSettings
from .prod import ProductionSettings

EnvironmentSettings = Type[AppBaseSettings]

_ENVIRONMENT_CLASS_MAP: dict[str, EnvironmentSettings] = {
    "development": DevelopmentSettings,
    "dev": DevelopmentSettings,
    "production": ProductionSettings,
    "prod": ProductionSettings,
}


def _read_env_hint() -> str | None:
    """Try to discover ENVIRONMENT value from the filesystem before instantiation"""
    candidate = os.environ.get("ENVIRONMENT")
    if candidate:
        return candidate

    env_file = Path(".env")
    if not env_file.exists():
        return None

    for line in env_file.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if line.startswith("ENVIRONMENT"):
            _, _, value = line.partition("=")
            return value.strip()
    return None


def _collect_env_files(env_name: str) -> list[Path]:
    env_candidates = [Path(".env"), Path(f".env.{env_name}")]
    return [path for path in env_candidates if path.exists()]


def _load_settings() -> AppBaseSettings:
    env_name = (_read_env_hint() or "development").strip().lower()
    settings_cls = _ENVIRONMENT_CLASS_MAP.get(env_name, DevelopmentSettings)

    env_files = _collect_env_files(env_name)
    configured_cls = settings_cls.with_env_files(env_files)
    settings = configured_cls()  # type: ignore[call-arg]
    return settings


settings: AppBaseSettings = _load_settings()

__all__ = ["settings", "AppBaseSettings", "DevelopmentSettings", "ProductionSettings"]
