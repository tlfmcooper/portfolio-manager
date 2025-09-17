"""
Main API router initialization.
"""
from fastapi import APIRouter

from app.api.v1 import api_router as api_v1_router
from app.core.config import settings

api_router = APIRouter()

# Include API v1 routes
api_router.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
    }
