from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppBaseSettings(BaseSettings):
    # --- App ---
    APP_NAME: str = Field(default="FastAPI Template", description="Human-readable application name")
    DEBUG: bool = Field(default=False, description="Enable debug behaviours like verbose logging")
    ENVIRONMENT: str = Field(default="development", description="Current environment name")
    VERSION: str = Field(default="0.1.0", description="Semantic application version")

    # --- API ---
    API_PREFIX: str = Field(default="/api", description="Global prefix for all API routes")

    # --- Database ---
    DATABASE_URL: AnyUrl = Field(..., description="Database DSN including driver, credentials, and host")
    AUTO_CREATE_SCHEMA: bool = Field(
        default=False,
        description="Create database schema on startup (development convenience only)",
    )

    # --- Server ---
    HOST: str = Field(default="0.0.0.0", description="Host interface exposed by ASGI server")
    PORT: int = Field(default=8000, description="Port FastAPI listens on")

    # --- Localization ---
    TIMEZONE: str = Field(default="UTC", description="IANA timezone name for app timestamps")

    # --- Alembic / migrations ---
    ALEMBIC_MIGRATION_PATH: str = Field(default="alembic", description="Path to Alembic migration directory")

    # --- Logging ---
    LOG_LEVEL: str = Field(default="INFO", description="Base log level for the application stack")
    AXIOM_DATASET_NAME: str = Field(default="production_loguru", description="Axiom dataset name for log ingestion", alias="AXIOM_DATASET")
    AXIOM_API_KEY: str = Field(default="", description="Axiom API key for log ingestion", alias="AXIOM_API_KEY")

    # Allow subclasses to influence default env files
    default_env_files: ClassVar[tuple[str, ...]] = (".env",)

    model_config = SettingsConfigDict(
        env_file=default_env_files,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @classmethod
    def with_env_files(cls, env_files: list[Path] | None) -> type["AppBaseSettings"]:
        class ConfiguredSettings(cls):  # type: ignore[misc, valid-type]
            model_config = SettingsConfigDict(
                env_file=tuple(str(path) for path in env_files) if env_files else cls.default_env_files,
                env_file_encoding="utf-8",
                case_sensitive=True,
                extra="ignore",
            )

        ConfiguredSettings.__name__ = f"Configured{cls.__name__}"
        return ConfiguredSettings
