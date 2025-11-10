from __future__ import annotations

from pathlib import Path
from typing import ClassVar, cast

from pydantic import AnyUrl, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.version import get_app_version


class AppBaseSettings(BaseSettings):
    # --- App ---
    APP_NAME: str = Field(default="FastAPI Template", description="Human-readable application name")
    DEBUG: bool = Field(default=False, description="Enable debug behaviours like verbose logging")
    ENVIRONMENT: str = Field(default="development", description="Current environment name")
    VERSION: str = Field(default_factory=get_app_version, description="Semantic application version (auto-derived from Git tags)")

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
    LOG_CONSOLE_ENABLED: bool = Field(default=True, description="Emit structured logs to stdout")
    AXIOM_LOGS_ENABLED: bool = Field(default=False, description="Forward logs to Axiom ingestion endpoint")
    AXIOM_DATASET_NAME: str = Field(default="production_loguru", description="Axiom dataset name for log ingestion", alias="AXIOM_DATASET")
    AXIOM_TRACES_DATASET_NAME: str = Field(
        default="",
        description="Optional separate Axiom dataset for distributed traces",
        alias="AXIOM_TRACES_DATASET",
    )
    AXIOM_API_KEY: str = Field(default="", description="Axiom API key for log ingestion", alias="AXIOM_API_KEY")
    AXIOM_BASE_URL: HttpUrl = Field(
        default=cast(HttpUrl, "https://api.axiom.co"),
        description="Base URL for Axiom ingestion APIs",
    )
    AXIOM_OTLP_ENDPOINT: HttpUrl = Field(
        default=cast(HttpUrl, "https://api.axiom.co/v1/traces"),
        description="OTLP HTTP endpoint for trace export",
    )
    AXIOM_LOG_BATCH_SIZE: int = Field(default=25, ge=1, description="Maximum number of log records per ingestion batch")
    AXIOM_LOG_FLUSH_INTERVAL_SECONDS: float = Field(
        default=2.0,
        ge=0.1,
        description="Flush interval for buffered log batches sent to Axiom",
    )
    AXIOM_REQUEST_TIMEOUT_SECONDS: float = Field(default=5.0, gt=0.0, description="Timeout in seconds for Axiom HTTP requests")

    # --- Tracing ---
    TRACING_ENABLED: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    TRACING_SAMPLE_RATIO: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Probability (0-1) of sampling new root spans",
    )

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
