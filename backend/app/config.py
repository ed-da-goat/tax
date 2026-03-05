"""
Application configuration via pydantic-settings.

Reads from environment variables or a .env file in the backend/ directory.
All secrets (JWT_SECRET, DATABASE_URL) must be set in the environment
or .env — never committed to version control.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the accounting system backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_NAME: str = "Georgia CPA Accounting System"
    DEBUG: bool = False

    # -----------------------------------------------------------------------
    # Database — PostgreSQL (async via asyncpg)
    # -----------------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ga_cpa"
    )
    # Synchronous URL for Alembic migrations
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ga_cpa"
    )

    # -----------------------------------------------------------------------
    # JWT Auth
    # -----------------------------------------------------------------------
    JWT_SECRET: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1-hour sessions (reduced from 8h for security)

    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = 50

    # -----------------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------------
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite default dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # -----------------------------------------------------------------------
    # File Storage
    # -----------------------------------------------------------------------
    DOCUMENT_STORAGE_PATH: str = "/data/documents"
    BACKUP_STORAGE_PATH: str = "/data/backups"


settings = Settings()
