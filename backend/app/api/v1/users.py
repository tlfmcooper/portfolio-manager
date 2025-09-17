"""
User management API routes.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import UserInDB, UserUpdate, UserProfile, UserPublic
from app.crud import get_user, update_user, get_users
from app.utils.dependencies import get_current_active_user, get_current_superuser
from app.models import User

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def read_user_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user profile.
    """
    return current_user


@router.put("/me", response_model=UserInDB)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user profile.
    """
    user = await update_user(db, current_user.id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/{user_id}", response_model=UserPublic)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user)
) -> Any:
    """
    Get user by ID (public information only).
    """
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/", response_model=List[UserPublic])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser)
) -> Any:
    """
    Get all users (superuser only).
    """
    users = await get_users(db, skip=skip, limit=limit)
    return users
