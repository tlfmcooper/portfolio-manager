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
    import os

    # Check database connectivity
    db_status = "unknown"
    try:
        # Try a simple query to verify database is accessible
        await db.execute("SELECT 1")
        db_status = "connected"
        db_file = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        db_exists = os.path.exists(db_file) if db_file.startswith(".") else True
    except Exception as e:
        db_status = f"error: {str(e)}"
        db_exists = False

    # Check Redis connectivity
    redis_status = "unknown"
    try:
        redis_client = await get_redis_client()
        redis_status = "connected" if redis_client.connected else "disconnected"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "url": (
                settings.DATABASE_URL.split("@")[-1]
                if "@" in settings.DATABASE_URL
                else "sqlite"
            ),
            "file_exists": db_exists if "sqlite" in settings.DATABASE_URL else None,
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
