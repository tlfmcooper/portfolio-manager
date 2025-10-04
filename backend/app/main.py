"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import chat, analysis
from app.core.config import settings
from app.core.redis_client import get_redis_client

app = FastAPI(
    title="Portfolio Manager API",
    description="AI-Powered Portfolio Management with Chat Assistant",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    redis_client = get_redis_client()
    await redis_client.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    redis_client = get_redis_client()
    await redis_client.disconnect()


@app.get("/")
async def root():
    return {
        "message": "Portfolio Manager API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
