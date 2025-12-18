"""
Database configuration and session management.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from pathlib import Path

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Determine if using SQLite or PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
is_postgres = settings.DATABASE_URL.startswith("postgresql")

# Ensure data directory exists for SQLite
if is_sqlite:
    # Extract database path from URL
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"[DATABASE] Using SQLite")
    print(f"[DATABASE] Directory: {db_file.parent.absolute()}")
    print(f"[DATABASE] File: {db_file.absolute()}")
elif is_postgres:
    # Log PostgreSQL connection (without password)
    if "@" in settings.DATABASE_URL:
        # Find the last @ symbol (which separates credentials from host)
        # Format: postgresql+asyncpg://user:password@host:port/database
        host_part = settings.DATABASE_URL.rsplit("@", 1)[1].split("/")[0]  # Get host:port only
        print(f"[DATABASE] Using PostgreSQL: {host_part}")
    else:
        print(f"[DATABASE] Using PostgreSQL: configured")

# Create async engine with appropriate settings
engine_kwargs = {
    "echo": settings.DATABASE_ECHO,
    "future": True,
}

# PostgreSQL-specific settings for Supabase pooler compatibility
if is_postgres:
    # Use NullPool for serverless/pooler connections (Supabase uses PgBouncer)
    engine_kwargs["poolclass"] = NullPool
    # Disable prepared statements for transaction pooling mode (asyncpg specific)
    engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {"jit": "off"}
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
