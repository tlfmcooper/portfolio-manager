"""Database model for per-user MCP API keys."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MCPAPIKey(Base):
    """Per-user MCP API key with one-time reveal secret storage."""

    __tablename__ = "mcp_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, default="Default MCP Key")
    key_prefix = Column(String(32), nullable=False, unique=True, index=True)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    permissions_json = Column(Text, nullable=False, default="[]")
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="mcp_api_keys")
