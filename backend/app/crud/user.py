"""
CRUD operations for user management.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models import User, Portfolio
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    stmt = select(User).where(User.email == email.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    stmt = select(User).where(User.username == username.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_email_or_username(db: AsyncSession, identifier: str) -> Optional[User]:
    """Get user by email or username."""
    # First try to get by username
    user = await get_user_by_username(db, identifier)
    if user:
        return user
    
    # If not found and identifier looks like email, try email
    if "@" in identifier:
        return await get_user_by_email(db, identifier)
    
    return None


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Get multiple users with pagination."""
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
