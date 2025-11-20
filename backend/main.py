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

import uvicorn
import shutil
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from app.core.config import settings
from app.core.database import create_tables
from app.api import api_router
from app.utils.dependencies import get_current_superuser
from app.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_tables()
    yield
    # Shutdown (if needed)
    pass


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

    print(f"CORS origins configured: {settings.BACKEND_CORS_ORIGINS}") # Debug print

    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
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
    current_user: User = Depends(get_current_superuser)
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
    
    db_path = Path("portfolio.db")
    
    # Backup existing database
    if db_path.exists():
        backup_path = Path("portfolio.db.backup")
        shutil.copy2(db_path, backup_path)
    
    # Write uploaded file
    try:
        with open(db_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "message": "Database uploaded successfully",
            "size_bytes": len(content),
            "backup_created": db_path.exists()
        }
    except Exception as e:
        # Restore backup if upload failed
        if backup_path.exists():
            shutil.copy2(backup_path, db_path)
        raise HTTPException(500, f"Upload failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info",
    )
