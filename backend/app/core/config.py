"""
Application configuration settings.
"""

import os
from typing import List, Any
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
    BACKEND_CORS_ORIGINS: Any = "*"  # Will be parsed by validator to List[str]

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

    # Exchange Rates API
    EXCHANGE_RATES_API_KEY: str = os.getenv("EXCHANGE_RATES_API_KEY", "")

    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    STOCK_DATA_CACHE_TTL: int = 3600  # 1 hour cache for stock data

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list.

        Accepts:
        - List[str]: Direct list like ['*'] or ['http://localhost:3000']
        - str: Comma-separated like "http://localhost:3000,http://localhost:8080"
        - str: JSON array like '["http://localhost:3000"]'
        - str: Single value like "*" or "http://localhost:3000"
        - None or empty string: defaults to ["*"]
        """
        # Handle None or empty string - default to allow all
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return ["*"]

        # Handle list input (already parsed)
        if isinstance(v, list):
            return [str(item) for item in v]  # Convert all items to strings

        # Handle string input
        if isinstance(v, str):
            # Single value (most common)
            if not v.startswith("[") and "," not in v:
                return [v.strip()]

            # Comma-separated values
            if "," in v and not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]

            # JSON array string - return as-is for Pydantic to parse
            if v.startswith("["):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                except json.JSONDecodeError:
                    pass

        raise ValueError(f"Invalid BACKEND_CORS_ORIGINS format: {v}")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env file


# Create settings instance
settings = Settings()
