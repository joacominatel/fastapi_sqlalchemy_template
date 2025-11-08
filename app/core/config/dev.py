from __future__ import annotations
from .base import AppBaseSettings

class DevelopmentSettings(AppBaseSettings):
    """Defaults tuned for local development workflows."""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    AUTO_CREATE_SCHEMA: bool = False
