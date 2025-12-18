"""
Main API router initialization.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.v1 import api_router as api_v1_router
from app.core.config import settings
from app.core.database import get_db, create_tables

api_router = APIRouter()

# Include API v1 routes
api_router.include_router(api_v1_router, prefix=settings.API_V1_STR)


# Health check endpoint
@api_router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint with database and Redis status."""
    from app.core.redis_client import get_redis_client
    from sqlalchemy import text
    import os

    # Determine database type
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    is_postgres = settings.DATABASE_URL.startswith("postgresql")
    db_type = "sqlite" if is_sqlite else ("postgresql" if is_postgres else "unknown")

    # Check database connectivity
    db_status = "unknown"
    db_exists = None
    try:
        # Try a simple query to verify database is accessible
        await db.execute(text("SELECT 1"))
        db_status = "connected"
        if is_sqlite:
            db_file = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
            db_exists = os.path.exists(db_file) if db_file.startswith(".") else True
    except Exception as e:
        db_status = f"error: {str(e)}"
        if is_sqlite:
            db_exists = False

    # Check Redis connectivity
    redis_status = "unknown"
    try:
        redis_client = await get_redis_client()
        redis_status = "connected" if redis_client.connected else "disconnected"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    # Build safe database URL for display (hide password)
    if "@" in settings.DATABASE_URL:
        db_url_display = settings.DATABASE_URL.split("@")[-1]
    elif is_sqlite:
        db_url_display = "sqlite:portfolio.db"
    else:
        db_url_display = "configured"

    return {
        "status": "healthy",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "type": db_type,
            "url": db_url_display,
            "file_exists": db_exists,
        },
        "redis": {
            "status": redis_status,
        },
    }


# Manual database initialization endpoint for troubleshooting
@api_router.post("/init-db")
async def initialize_database():
    """
    Manually initialize database tables.
    Useful for troubleshooting Railway deployments.
    """
    try:
        await create_tables()
        return {
            "status": "success",
            "message": "Database tables created successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize database: {str(e)}",
        )
