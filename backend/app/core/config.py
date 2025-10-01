"""
Application configuration settings.
"""

import os
from typing import List
from pydantic import validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Basic app settings
    PROJECT_NAME: str = "Portfolio Dashboard API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "API for managing user portfolios and analyzing investment performance"
    )
    API_V1_STR: str = "/api/v1"

    # Security settings
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./portfolio.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "*"
    ]  # TEMPORARY: Allow all origins for debugging CORS

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Testing
    TESTING: bool = False
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Password settings
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Finnhub API
    FINNHUB_API_KEY: str

    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    STOCK_DATA_CACHE_TTL: int = 3600  # 1 hour cache for stock data

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env file


# Create settings instance
settings = Settings()
