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
    # Check environment variable first
    candidate = os.environ.get("ENVIRONMENT")
    if candidate:
        return candidate

    # Only read file if env var not set
    env_file = Path(".env")
    if not env_file.exists():
        return None

    # Read file once and parse efficiently
    try:
        content = env_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue
            # Check for ENVIRONMENT key
            if stripped.startswith("ENVIRONMENT="):
                return stripped.split("=", 1)[1].strip()
    except (OSError, UnicodeDecodeError):
        # Gracefully handle file read errors
        return None
    
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
