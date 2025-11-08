from __future__ import annotations
from .base import AppBaseSettings

class ProductionSettings(AppBaseSettings):
    """Defaults tuned for production deployments"""

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    AUTO_CREATE_SCHEMA: bool = False
