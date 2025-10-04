"""
Application Configuration
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Portfolio Manager"

    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # Chat Settings
    CHAT_SESSION_TTL: int = 2592000  # 30 days in seconds
    DASHBOARD_CACHE_TTL: int = 300  # 5 minutes
    MARKET_DATA_CACHE_TTL: int = 60  # 1 minute

    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Anthropic API
    ANTHROPIC_API_KEY: str = ""

    # Database (for future use)
    DATABASE_URL: str = "sqlite:///./portfolio.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
