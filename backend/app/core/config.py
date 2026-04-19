"""
Application configuration settings.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Any, Optional


_ORIGINAL_ENV_KEYS = set(os.environ)


def _load_env_file(env_path: Path, *, allow_file_override: bool = False) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in _ORIGINAL_ENV_KEYS:
            continue
        if not allow_file_override and key in os.environ:
            continue
        os.environ[key] = value


_ENV_DIR = Path(__file__).resolve().parents[2]
_load_env_file(_ENV_DIR / ".env")
_load_env_file(_ENV_DIR / ".env.local", allow_file_override=True)


def build_database_url() -> str:
    """
    Build the database URL from environment variables.
    Priority:
    1. DATABASE_URL if explicitly set (PostgreSQL connection string)
    2. Fallback to SQLite for local development

    For Supabase, get the connection string from:
    Supabase Dashboard > Project Settings > Database > Connection string > URI
    Choose "Transaction" mode (port 6543) for serverless/pooled connections.
    """
    from urllib.parse import quote_plus

    # Check for explicit DATABASE_URL first
    explicit_db_url = os.getenv("DATABASE_URL")
    if explicit_db_url:
        explicit_db_url = explicit_db_url.strip()

    if explicit_db_url and not explicit_db_url.startswith("sqlite"):
        # Handle PostgreSQL URLs with special characters in password
        url = explicit_db_url

        # Convert postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        # Parse and URL-encode password if needed (handles @ # ! etc in password)
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            rest = url.replace("postgresql://", "")
            last_at_idx = rest.rfind("@")

            if last_at_idx != -1:
                credentials = rest[:last_at_idx]
                host_and_db = rest[last_at_idx + 1:]

                first_colon_idx = credentials.find(":")
                if first_colon_idx != -1:
                    user = credentials[:first_colon_idx]
                    password = credentials[first_colon_idx + 1:]
                    encoded_password = quote_plus(password)
                    url = f"postgresql+asyncpg://{user}:{encoded_password}@{host_and_db}"
                else:
                    url = f"postgresql+asyncpg://{credentials}@{host_and_db}"
            else:
                url = f"postgresql+asyncpg://{rest}"

        return url

    # Fallback to SQLite for local development
    return "sqlite+aiosqlite:///./portfolio.db"


def _parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | int | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _parse_cors_origins(value: Any) -> List[str]:
    """Parse CORS origins from string or list."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return ["*"]

    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, str):
        if not value.startswith("[") and "," not in value:
            return [value.strip()]

        if "," in value and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]

        if value.startswith("["):
            import json

            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]

    raise ValueError(f"Invalid BACKEND_CORS_ORIGINS format: {value}")


@dataclass(slots=True)
class Settings:
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "Portfolio Dashboard API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for managing user portfolios and analyzing investment performance"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./portfolio.db"
    DATABASE_ECHO: bool = False
    BACKEND_CORS_ORIGINS: List[str] | str = "*"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    TESTING: bool = False
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    FINNHUB_API_KEY: str = ""
    EXCHANGE_RATES_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    WS_HEARTBEAT_INTERVAL: int = 30
    STOCK_DATA_CACHE_TTL: int = 3600
    ADMIN_UPLOAD_TOKEN: str = ""
    MCP_ENABLED: bool = True
    MCP_ROUTE_PREFIX: str = "/mcp"
    MCP_PROTOCOL_VERSION: str = "2025-03-26"
    MCP_SERVER_NAME: str = "portfolio-manager-mcp"
    MCP_CONFIG_PATH: str = ""
    MCP_ENABLE_SSE: bool = True
    MCP_SSE_HEARTBEAT_INTERVAL: int = 10
    MCP_API_KEYS_JSON: str = ""
    BARCHART_PROXY_URL: Optional[str] = None

    def __post_init__(self) -> None:
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", self.PROJECT_NAME)
        self.VERSION = os.getenv("VERSION", self.VERSION)
        self.DESCRIPTION = os.getenv("DESCRIPTION", self.DESCRIPTION)
        self.API_V1_STR = os.getenv("API_V1_STR", self.API_V1_STR)
        self.SECRET_KEY = os.getenv("SECRET_KEY", self.SECRET_KEY)
        self.ALGORITHM = os.getenv("ALGORITHM", self.ALGORITHM)
        self.ACCESS_TOKEN_EXPIRE_MINUTES = _parse_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), self.ACCESS_TOKEN_EXPIRE_MINUTES)
        self.REFRESH_TOKEN_EXPIRE_MINUTES = _parse_int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"), self.REFRESH_TOKEN_EXPIRE_MINUTES)
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.DATABASE_URL = build_database_url()
        self.DATABASE_ECHO = _parse_bool(os.getenv("DATABASE_ECHO"), self.DATABASE_ECHO)
        self.BACKEND_CORS_ORIGINS = _parse_cors_origins(os.getenv("BACKEND_CORS_ORIGINS", self.BACKEND_CORS_ORIGINS))
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", self.ENVIRONMENT)
        self.DEBUG = _parse_bool(os.getenv("DEBUG"), self.DEBUG)
        self.TESTING = _parse_bool(os.getenv("TESTING"), self.TESTING)
        self.TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", self.TEST_DATABASE_URL)
        self.PASSWORD_MIN_LENGTH = _parse_int(os.getenv("PASSWORD_MIN_LENGTH"), self.PASSWORD_MIN_LENGTH)
        self.PASSWORD_REQUIRE_UPPERCASE = _parse_bool(os.getenv("PASSWORD_REQUIRE_UPPERCASE"), self.PASSWORD_REQUIRE_UPPERCASE)
        self.PASSWORD_REQUIRE_LOWERCASE = _parse_bool(os.getenv("PASSWORD_REQUIRE_LOWERCASE"), self.PASSWORD_REQUIRE_LOWERCASE)
        self.PASSWORD_REQUIRE_DIGITS = _parse_bool(os.getenv("PASSWORD_REQUIRE_DIGITS"), self.PASSWORD_REQUIRE_DIGITS)
        self.PASSWORD_REQUIRE_SPECIAL = _parse_bool(os.getenv("PASSWORD_REQUIRE_SPECIAL"), self.PASSWORD_REQUIRE_SPECIAL)
        self.RATE_LIMIT_PER_MINUTE = _parse_int(os.getenv("RATE_LIMIT_PER_MINUTE"), self.RATE_LIMIT_PER_MINUTE)
        self.FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", self.FINNHUB_API_KEY)
        self.EXCHANGE_RATES_API_KEY = os.getenv("EXCHANGE_RATES_API_KEY", self.EXCHANGE_RATES_API_KEY)
        self.REDIS_URL = os.getenv("REDIS_URL", self.REDIS_URL)
        self.WS_HEARTBEAT_INTERVAL = _parse_int(os.getenv("WS_HEARTBEAT_INTERVAL"), self.WS_HEARTBEAT_INTERVAL)
        self.STOCK_DATA_CACHE_TTL = _parse_int(os.getenv("STOCK_DATA_CACHE_TTL"), self.STOCK_DATA_CACHE_TTL)
        self.ADMIN_UPLOAD_TOKEN = os.getenv("ADMIN_UPLOAD_TOKEN", self.ADMIN_UPLOAD_TOKEN)
        self.MCP_ENABLED = _parse_bool(os.getenv("MCP_ENABLED"), self.MCP_ENABLED)
        self.MCP_ROUTE_PREFIX = os.getenv("MCP_ROUTE_PREFIX", self.MCP_ROUTE_PREFIX)
        self.MCP_PROTOCOL_VERSION = os.getenv("MCP_PROTOCOL_VERSION", self.MCP_PROTOCOL_VERSION)
        self.MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", self.MCP_SERVER_NAME)
        self.MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", self.MCP_CONFIG_PATH)
        self.MCP_ENABLE_SSE = _parse_bool(os.getenv("MCP_ENABLE_SSE"), self.MCP_ENABLE_SSE)
        self.MCP_SSE_HEARTBEAT_INTERVAL = _parse_int(os.getenv("MCP_SSE_HEARTBEAT_INTERVAL"), self.MCP_SSE_HEARTBEAT_INTERVAL)
        self.MCP_API_KEYS_JSON = os.getenv("MCP_API_KEYS_JSON", self.MCP_API_KEYS_JSON)
        self.BARCHART_PROXY_URL = os.getenv("BARCHART_PROXY_URL") or None


# Create settings instance
settings = Settings()
