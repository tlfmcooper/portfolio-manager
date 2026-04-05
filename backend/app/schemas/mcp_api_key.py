"""Schemas for per-user MCP API key management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MCPAPIKeyCreateRequest(BaseModel):
    name: str = Field(default="Default MCP Key", min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class MCPAPIKeyInfo(BaseModel):
    id: int
    name: str
    key_prefix: str
    key_preview: str
    permissions: list[str]
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MCPAPIKeySecretResponse(BaseModel):
    api_key: str
    key: MCPAPIKeyInfo
