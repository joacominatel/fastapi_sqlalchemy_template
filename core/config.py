from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl, Field


class Settings(BaseSettings):
    """Global application configuration, loaded automatically from .env."""

    # --- App ---
    APP_NAME: str = "FastAPI Template"
    DEBUG: bool = Field(default=False, description="Enable debug logging and verbose SQL output")
    ENVIRONMENT: str = Field(default="development", description="Environment name: development/staging/production")

    # --- Database ---
    DATABASE_URL: AnyUrl = Field(..., description="Full database URL with driver, e.g. postgres+asyncpg://user:pass@db/app")

    # --- Server ---
    HOST: str = Field(default="0.0.0.0", description="Host address to bind the FastAPI server")
    PORT: int = Field(default=8000, description="Port to run the FastAPI app on")

    # --- Alembic / migrations ---
    ALEMBIC_MIGRATION_PATH: str = Field(default="migrations", description="Path to Alembic migration directory")

    # --- Misc ---
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")

    # --- Model configuration ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Single shared instance across the project
settings = Settings()
