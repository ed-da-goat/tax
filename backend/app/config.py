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
    # Must be set in .env — no default (prevents accidental use of wrong DB)
    # -----------------------------------------------------------------------
    DATABASE_URL: str
    # Synchronous URL for Alembic migrations
    DATABASE_URL_SYNC: str = ""

    # -----------------------------------------------------------------------
    # Encryption — Fernet symmetric key for PII at rest
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Must be set in .env — no default
    # -----------------------------------------------------------------------
    ENCRYPTION_KEY: str

    # -----------------------------------------------------------------------
    # JWT Auth — Must be set in .env — no default
    # -----------------------------------------------------------------------
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30-minute sessions

    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = 50

    # -----------------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------------
    CORS_ORIGINS: list[str] = [
        "https://localhost",
        "https://192.168.1.104",
        "http://localhost:5173",  # Vite dev server (DEBUG only)
        "http://localhost:3000",  # Vite dev server port 3000
    ]

    # -----------------------------------------------------------------------
    # File Storage
    # -----------------------------------------------------------------------
    DOCUMENT_STORAGE_PATH: str = "/data/documents"
    BACKUP_STORAGE_PATH: str = "/data/backups"

    # -----------------------------------------------------------------------
    # Email (SMTP)
    # -----------------------------------------------------------------------
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Georgia CPA Firm"
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True


settings = Settings()
