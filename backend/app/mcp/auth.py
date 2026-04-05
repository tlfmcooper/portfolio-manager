"""Authentication and permission helpers for MCP requests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import authenticate_user_mcp_api_key, touch_mcp_api_key_last_used
from app.core.security import verify_token
from app.crud import get_user_by_username
from app.mcp.constants import DEFAULT_USER_MCP_PERMISSIONS
from app.mcp.errors import MCPError
from app.mcp.errors import forbidden, unauthorized


DEFAULT_AUTHENTICATED_PERMISSIONS = set(DEFAULT_USER_MCP_PERMISSIONS)


@dataclass(slots=True)
class MCPAPIKeyConfig:
    permissions: Set[str] = field(default_factory=set)
    username: Optional[str] = None
    subject: Optional[str] = None
    is_superuser: bool = False


@dataclass(slots=True)
class MCPAuthContext:
    auth_type: str = "anonymous"
    subject: Optional[str] = None
    username: Optional[str] = None
    is_authenticated: bool = False
    is_superuser: bool = False
    permissions: Set[str] = field(default_factory=set)

    def has_permissions(self, required: Iterable[str]) -> bool:
        required_set = set(required)
        if not required_set:
            return True
        return "*" in self.permissions or required_set.issubset(self.permissions)


def _parse_api_key_config(api_key: str, raw_config: object) -> MCPAPIKeyConfig:
    if isinstance(raw_config, list):
        return MCPAPIKeyConfig(permissions={str(scope) for scope in raw_config})

    if isinstance(raw_config, str):
        return MCPAPIKeyConfig(permissions={segment.strip() for segment in raw_config.split(",") if segment.strip()})

    if isinstance(raw_config, dict):
        raw_permissions = raw_config.get("permissions", raw_config.get("scopes", []))
        permissions: Set[str]
        if isinstance(raw_permissions, list):
            permissions = {str(scope) for scope in raw_permissions}
        elif isinstance(raw_permissions, str):
            permissions = {segment.strip() for segment in raw_permissions.split(",") if segment.strip()}
        else:
            permissions = set()

        username = raw_config.get("username")
        subject = raw_config.get("subject") or username or f"api-key:{api_key}"
        is_superuser = bool(raw_config.get("is_superuser", False))
        if is_superuser:
            permissions.add("*")

        return MCPAPIKeyConfig(
            permissions=permissions,
            username=str(username) if username else None,
            subject=str(subject) if subject else None,
            is_superuser=is_superuser,
        )

    return MCPAPIKeyConfig()


def _load_api_key_map() -> dict[str, MCPAPIKeyConfig]:
    raw = settings.MCP_API_KEYS_JSON.strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    api_keys: dict[str, MCPAPIKeyConfig] = {}
    for api_key, raw_config in parsed.items():
        api_keys[str(api_key)] = _parse_api_key_config(str(api_key), raw_config)
    return api_keys


async def build_auth_context(
    db: AsyncSession,
    authorization: Optional[str],
    api_key: Optional[str],
) -> MCPAuthContext:
    """Build an auth context from bearer token or API key headers."""
    if api_key:
        authenticated_key = await authenticate_user_mcp_api_key(db, api_key)
        if authenticated_key:
            user, key_record, permissions = authenticated_key
            await touch_mcp_api_key_last_used(db, key_record)
            permission_set = set(permissions or DEFAULT_USER_MCP_PERMISSIONS)
            if user.is_superuser:
                permission_set.add("*")
            return MCPAuthContext(
                auth_type="api_key",
                subject=str(user.id),
                username=user.username,
                is_authenticated=True,
                is_superuser=bool(user.is_superuser),
                permissions=permission_set,
            )

    api_keys = _load_api_key_map()
    if api_key and api_key in api_keys:
        api_key_config = api_keys[api_key]
        return MCPAuthContext(
            auth_type="api_key",
            subject=api_key_config.subject or f"api-key:{api_key}",
            username=api_key_config.username,
            is_authenticated=True,
            is_superuser=api_key_config.is_superuser,
            permissions=api_key_config.permissions or {"*"},
        )

    if not authorization:
        return MCPAuthContext(permissions={"resources:read", "prompts:read", "market:read", "exchange:read"})

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized(message="Invalid authorization header")

    try:
        payload = verify_token(token, "access")
        username = payload.get("sub")
        if not username:
            raise unauthorized(message="JWT token payload did not include subject")

        user = await get_user_by_username(db, username)
        if not user or not user.is_active:
            raise unauthorized(message="User not found or inactive")

        permissions = set(DEFAULT_AUTHENTICATED_PERMISSIONS)
        if user.is_superuser:
            permissions.add("*")

        return MCPAuthContext(
            auth_type="bearer",
            subject=str(user.id),
            username=user.username,
            is_authenticated=True,
            is_superuser=bool(user.is_superuser),
            permissions=permissions,
        )
    except MCPError:
        raise
    except Exception as exc:
        raise unauthorized(message="Could not validate bearer token") from exc


def enforce_access(context: MCPAuthContext, requires_auth: bool, permissions: Iterable[str]) -> None:
    """Enforce auth and permission requirements for a capability."""
    if requires_auth and not context.is_authenticated:
        raise unauthorized()
    if not context.has_permissions(permissions):
        raise forbidden(message="Request does not satisfy capability permissions")