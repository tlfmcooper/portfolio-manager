"""
User management API routes.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import MCPAPIKeyCreateRequest, MCPAPIKeyInfo, MCPAPIKeySecretResponse, UserInDB, UserUpdate, UserProfile, UserPublic
from app.crud import (
    create_user_mcp_api_key,
    get_user,
    get_user_mcp_api_key,
    get_users,
    list_user_mcp_api_keys,
    revoke_user_mcp_api_key,
    rotate_user_mcp_api_key,
    serialize_mcp_api_key,
    update_user,
)
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


@router.get("/me/mcp-api-keys", response_model=List[MCPAPIKeyInfo])
async def list_my_mcp_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    keys = await list_user_mcp_api_keys(db, current_user.id)
    return [serialize_mcp_api_key(api_key) for api_key in keys]


@router.post("/me/mcp-api-keys", response_model=MCPAPIKeySecretResponse, status_code=status.HTTP_201_CREATED)
async def create_my_mcp_api_key(
    request: MCPAPIKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    api_key, raw_key = await create_user_mcp_api_key(
        db,
        current_user,
        name=request.name,
        expires_in_days=request.expires_in_days,
    )
    return {"api_key": raw_key, "key": serialize_mcp_api_key(api_key)}


@router.post("/me/mcp-api-keys/{key_id}/rotate", response_model=MCPAPIKeySecretResponse)
async def rotate_my_mcp_api_key(
    key_id: int,
    request: MCPAPIKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    api_key = await get_user_mcp_api_key(db, current_user.id, key_id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP API key not found")

    rotated_key, raw_key = await rotate_user_mcp_api_key(db, api_key, expires_in_days=request.expires_in_days)
    if request.name != api_key.name:
        rotated_key.name = request.name
        await db.commit()
        await db.refresh(rotated_key)

    return {"api_key": raw_key, "key": serialize_mcp_api_key(rotated_key)}


@router.delete("/me/mcp-api-keys/{key_id}")
async def revoke_my_mcp_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    api_key = await get_user_mcp_api_key(db, current_user.id, key_id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP API key not found")

    await revoke_user_mcp_api_key(db, api_key)
    return {"message": "MCP API key revoked"}
