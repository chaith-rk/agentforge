"""Application settings loaded from environment variables.

Uses pydantic-settings to load configuration from .env files and environment
variables. Secrets are never hardcoded — always loaded from the environment.
"""

from __future__ import annotations

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    All sensitive values (API keys, encryption keys) must be provided via
    environment variables or .env file. No defaults for secrets.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Vapi integration
    vapi_api_key: str = ""
    vapi_webhook_secret: str = ""
    vapi_assistant_id: str = ""
    vapi_phone_number_id: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///data/calls.db"

    # API security
    api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]

    # Application
    log_level: str = "INFO"
    environment: Environment = Environment.DEVELOPMENT

    # PII encryption (Fernet key — generate with scripts/generate_encryption_key.py)
    pii_encryption_key: str = ""

    # WebSocket
    websocket_ping_interval: int = 30

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


# Singleton instance
settings = Settings()
