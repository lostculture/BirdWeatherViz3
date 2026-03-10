"""
Application Configuration
Handles environment variables and application settings.

Version: 1.0.0
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "BirdWeatherViz3"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./data/db/birdweather.db"

    # Security
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-RANDOM-STRING"
    JWT_SECRET: str = "CHANGE-ME-IN-PRODUCTION-USE-RANDOM-STRING"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    CONFIG_PASSWORD: str = "changeme"

    # CORS - For public deployment, set specific origins
    # For local development: ["http://localhost:3001", "http://127.0.0.1:3001"]
    # For production: ["https://your-domain.com"]
    CORS_ORIGINS: list = ["http://localhost:3001", "http://127.0.0.1:3001"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: list = ["Authorization", "Content-Type"]

    # Auto-Update Settings
    AUTO_UPDATE_ENABLED: bool = True
    AUTO_UPDATE_INTERVAL: int = 3600  # 1 hour in seconds

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = True
    LOG_FILE_PATH: str = "./data/logs/app.log"

    # File Uploads
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # External APIs
    BIRDWEATHER_API_URL: str = "https://app.birdweather.com/api/v1"
    OPENMETEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"

    # Wikimedia
    WIKIMEDIA_USER_AGENT: str = "BirdWeatherViz3/1.0 (https://github.com/lostculture/BirdWeatherViz3)"
    WIKIMEDIA_EMAIL: Optional[str] = None

    # Pagination
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid re-reading .env file on every call.
    """
    return Settings()


# Convenience exports
settings = get_settings()
