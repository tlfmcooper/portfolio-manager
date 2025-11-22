"""Main FastAPI application."""

import os
from contextlib import asynccontextmanager
from typing import List, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_tables
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_tables()

    # Initialize Redis connection
    from app.core.redis_client import get_redis_client

    redis_client = await get_redis_client()

    yield

    # Shutdown
    if redis_client:
        await redis_client.disconnect()


def _build_cors_config() -> Tuple[List[str], bool]:
    """Return origins list and allow_credentials flag for FastAPI CORS middleware."""

    origins: List[str] = list(settings.BACKEND_CORS_ORIGINS or ["*"])
    allow_all = any(origin == "*" for origin in origins)

    if allow_all:
        # Wildcard origins cannot be combined with allow_credentials=True
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )
