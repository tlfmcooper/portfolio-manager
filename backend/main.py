#!/usr/bin/env python3
"""
Portfolio Dashboard API - Main Entry Point

New, completely rewritten authentication system with:
- Async/await throughout
- Proper JWT token management
- Secure password hashing
- Clean API structure
- Modern SQLAlchemy async ORM
- Comprehensive error handling
"""

import os
import secrets
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Tuple

import uvicorn
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.core.config import settings
from app.core.database import create_tables, get_db
from app.core.security import verify_token
from app.crud import get_user_by_username
from app.models import User
from app.utils.dependencies import get_current_superuser


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_tables()
    yield
    # Shutdown (if needed)
    pass


def _build_cors_config() -> Tuple[List[str], bool]:
    origins: List[str] = list(settings.BACKEND_CORS_ORIGINS or ["*"])
    allow_all = any(origin == "*" for origin in origins)

    if allow_all:
        return ["*"], False

    dev_origins = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    }

    local_dev_ip = os.getenv("DEV_LOCAL_IP") or os.getenv("LOCAL_DEV_IP")
    if local_dev_ip:
        dev_origins.add(f"http://{local_dev_ip}:5173")
        dev_origins.add(f"http://{local_dev_ip}:4173")

    if settings.DEBUG:
        origins = list({*origins, *dev_origins})

    return origins, True


def create_application() -> FastAPI:
    """Create FastAPI application with all configurations."""

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    cors_origins, allow_credentials = _build_cors_config()

    # Set up CORS middleware - Allow local development origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router)

    return app


# Create the application instance
app = create_application()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs_url": "/docs" if settings.DEBUG else None,
    }


# Admin endpoint for database upload (requires superuser authentication)
@app.post("/admin/upload-db")
async def upload_database(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None, alias="Authorization"),
    admin_token: str | None = Header(default=None, alias="x-admin-token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload portfolio.db file to replace current database.
    ⚠️ WARNING: This will overwrite the existing database!
    🔒 PROTECTED: Requires superuser authentication

    Usage:
    1. Login to get JWT token: POST /api/v1/auth/login
    2. Upload database with Authorization header: Bearer <token>
    """
    if file.filename != "portfolio.db":
        raise HTTPException(400, "File must be named portfolio.db")

    authorized = False
    if settings.ADMIN_UPLOAD_TOKEN and admin_token:
        if secrets.compare_digest(settings.ADMIN_UPLOAD_TOKEN, admin_token):
            authorized = True

    if not authorized:
        if not authorization:
            raise HTTPException(status_code=401, detail="Not authenticated")

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        payload = verify_token(token, "access")
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        user = await get_user_by_username(db, username)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials"
            )

        if not user.is_superuser:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get database path from settings
    db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace(
        "sqlite:///", ""
    )
    db_path = Path(db_url)

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path = None

    # Backup existing database
    if db_path.exists():
        backup_path = db_path.parent / f"{db_path.name}.backup"
        shutil.copy2(db_path, backup_path)

    # Write uploaded file
    try:
        with open(db_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return {
            "message": "Database uploaded successfully",
            "size_bytes": len(content),
            "backup_created": backup_path is not None,
            "database_path": str(db_path),
        }
    except Exception as e:
        # Restore backup if upload failed
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, db_path)
        raise HTTPException(500, f"Upload failed: {str(e)}")


# Admin endpoint to warm Redis cache (requires superuser authentication)
@app.post("/admin/warm-cache")
async def warm_cache_endpoint(current_user: User = Depends(get_current_superuser)):
    """
    Warm up Redis cache with stock data from portfolio.
    🔒 PROTECTED: Requires superuser authentication

    This will fetch and cache:
    - Stock quotes for all portfolio holdings
    - Exchange rates
    """
    from app.services.finnhub_service import FinnhubService
    from app.services.exchange_rate_service import ExchangeRateService
    from app.core.redis_client import get_redis_client
    from app.core.database import get_db
    from sqlalchemy import select
    from app.models import Holding

    redis_client = await get_redis_client()
    finnhub = FinnhubService(settings.FINNHUB_API_KEY)
    exchange_service = ExchangeRateService(settings.EXCHANGE_RATES_API_KEY)

    cached_count = 0
    failed_count = 0

    # Get unique symbols from database
    async for session in get_db():
        result = await session.execute(select(Holding.symbol).distinct())
        symbols = [row[0] for row in result.all() if row[0]]
        break

    # Cache stock quotes
    for symbol in symbols:
        try:
            quote = await finnhub.get_quote(symbol)
            if quote:
                cache_key = f"stock:quote:{symbol}"
                await redis_client.set(
                    cache_key, quote, ttl=settings.STOCK_DATA_CACHE_TTL
                )
                cached_count += 1
        except Exception:
            failed_count += 1

    # Cache exchange rates
    try:
        await exchange_service.get_exchange_rates("USD")
    except Exception:
        pass

    return {
        "message": "Cache warming complete",
        "symbols_cached": cached_count,
        "symbols_failed": failed_count,
        "total_symbols": len(symbols),
    }


# Admin endpoint to create first superuser (protected by token)
@app.post("/admin/create-first-superuser")
async def create_first_superuser(
    admin_token: str | None = Header(default=None, alias="x-admin-token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create the first superuser account.
    🔒 PROTECTED: Requires ADMIN_UPLOAD_TOKEN environment variable

    This endpoint is for initial setup when no users exist yet.
    After creating the first superuser, use normal authentication.
    """
    from sqlalchemy import select
    from app.core.security import get_password_hash

    # Verify admin token
    if not settings.ADMIN_UPLOAD_TOKEN or not admin_token:
        raise HTTPException(
            status_code=401,
            detail="Admin token required. Set ADMIN_UPLOAD_TOKEN environment variable.",
        )

    if not secrets.compare_digest(settings.ADMIN_UPLOAD_TOKEN, admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")

    # Check if user already exists
    result = await db.execute(select(User).where(User.username == "alkhaf"))
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        user.hashed_password = get_password_hash("Password123")
        user.is_active = True
        user.is_superuser = True
        user.email = "developer0.ali1@gmail.com"
        await db.commit()
        return {
            "message": "Superuser updated successfully",
            "username": "alkhaf",
            "email": "developer0.ali1@gmail.com",
            "password": "Password123",
        }
    else:
        # Create new user
        new_user = User(
            username="alkhaf",
            email="developer0.ali1@gmail.com",
            full_name="Ali Khaf",
            hashed_password=get_password_hash("Password123"),
            is_active=True,
            is_superuser=True,
        )
        db.add(new_user)
        await db.commit()
        return {
            "message": "Superuser created successfully",
            "username": "alkhaf",
            "email": "developer0.ali1@gmail.com",
            "password": "Password123",
        }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info",
    )
