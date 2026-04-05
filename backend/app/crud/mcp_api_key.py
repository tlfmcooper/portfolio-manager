"""CRUD helpers for per-user MCP API keys."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.constants import DEFAULT_USER_MCP_PERMISSIONS
from app.models import MCPAPIKey, User


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _serialize_permissions(permissions: list[str]) -> str:
    return json.dumps(sorted(set(permissions)))


def _deserialize_permissions(raw_permissions: str | None) -> list[str]:
    if not raw_permissions:
        return list(DEFAULT_USER_MCP_PERMISSIONS)
    try:
        parsed = json.loads(raw_permissions)
    except json.JSONDecodeError:
        return list(DEFAULT_USER_MCP_PERMISSIONS)
    if not isinstance(parsed, list):
        return list(DEFAULT_USER_MCP_PERMISSIONS)
    return [str(permission) for permission in parsed]


def _generate_raw_api_key() -> tuple[str, str]:
    key_prefix = f"pmcp_{secrets.token_hex(4)}"
    raw_key = f"{key_prefix}.{secrets.token_urlsafe(32)}"
    return key_prefix, raw_key


def _key_preview(key_prefix: str) -> str:
    return f"{key_prefix}..."


async def list_user_mcp_api_keys(db: AsyncSession, user_id: int) -> list[MCPAPIKey]:
    stmt = select(MCPAPIKey).where(MCPAPIKey.user_id == user_id).order_by(MCPAPIKey.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user_mcp_api_key(db: AsyncSession, user_id: int, key_id: int) -> Optional[MCPAPIKey]:
    stmt = select(MCPAPIKey).where(MCPAPIKey.id == key_id, MCPAPIKey.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user_mcp_api_key(
    db: AsyncSession,
    user: User,
    name: str,
    expires_in_days: Optional[int] = None,
    permissions: Optional[list[str]] = None,
) -> tuple[MCPAPIKey, str]:
    key_prefix, raw_key = _generate_raw_api_key()
    api_key = MCPAPIKey(
        user_id=user.id,
        name=name,
        key_prefix=key_prefix,
        key_hash=_hash_api_key(raw_key),
        permissions_json=_serialize_permissions(permissions or list(DEFAULT_USER_MCP_PERMISSIONS)),
        expires_at=(datetime.utcnow() + timedelta(days=expires_in_days)) if expires_in_days else None,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


async def rotate_user_mcp_api_key(
    db: AsyncSession,
    api_key: MCPAPIKey,
    expires_in_days: Optional[int] = None,
) -> tuple[MCPAPIKey, str]:
    key_prefix, raw_key = _generate_raw_api_key()
    api_key.key_prefix = key_prefix
    api_key.key_hash = _hash_api_key(raw_key)
    api_key.last_used_at = None
    api_key.revoked_at = None
    api_key.is_active = True
    if expires_in_days is not None:
        api_key.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    api_key.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


async def revoke_user_mcp_api_key(db: AsyncSession, api_key: MCPAPIKey) -> MCPAPIKey:
    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()
    api_key.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(api_key)
    return api_key


async def authenticate_user_mcp_api_key(db: AsyncSession, raw_key: str) -> Optional[tuple[User, MCPAPIKey, list[str]]]:
    stmt = (
        select(MCPAPIKey, User)
        .join(User, User.id == MCPAPIKey.user_id)
        .where(MCPAPIKey.key_hash == _hash_api_key(raw_key), MCPAPIKey.is_active == True, User.is_active == True)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    api_key, user = row
    if api_key.expires_at and api_key.expires_at <= datetime.utcnow():
        return None

    return user, api_key, _deserialize_permissions(api_key.permissions_json)


async def touch_mcp_api_key_last_used(db: AsyncSession, api_key: MCPAPIKey) -> None:
    now = datetime.utcnow()
    if api_key.last_used_at and (now - api_key.last_used_at) < timedelta(minutes=5):
        return

    api_key.last_used_at = now
    api_key.updated_at = now
    await db.commit()


def serialize_mcp_api_key(api_key: MCPAPIKey) -> dict:
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "key_preview": _key_preview(api_key.key_prefix),
        "permissions": _deserialize_permissions(api_key.permissions_json),
        "is_active": api_key.is_active,
        "last_used_at": api_key.last_used_at,
        "expires_at": api_key.expires_at,
        "revoked_at": api_key.revoked_at,
        "created_at": api_key.created_at,
        "updated_at": api_key.updated_at,
    }
