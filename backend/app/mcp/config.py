"""Config loading for embedded MCP capabilities."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.mcp.errors import internal_error


class ToolConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    handler: str
    requiresAuth: bool = True
    permissions: List[str] = Field(default_factory=list)
    inputSchema: Dict[str, Any] = Field(default_factory=dict)
    outputSchema: Optional[Dict[str, Any]] = None
    annotations: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_tool_name(cls, value: str) -> str:
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not value or any(char not in allowed_chars for char in value):
            raise ValueError("Tool names may only contain [a-z0-9_-]")
        return value


class ResourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    handler: str
    mimeType: str = "application/json"
    uri: Optional[str] = None
    uriTemplate: Optional[str] = None
    requiresAuth: bool = True
    permissions: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class PromptArgumentConfig(BaseModel):
    name: str
    description: str
    required: bool = False


class PromptConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    handler: str
    arguments: List[PromptArgumentConfig] = Field(default_factory=list)


class MCPServerMetadata(BaseModel):
    name: str
    version: str
    instructions: str


class MCPCapabilityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: MCPServerMetadata
    tools: List[ToolConfig] = Field(default_factory=list)
    resources: List[ResourceConfig] = Field(default_factory=list)
    prompts: List[PromptConfig] = Field(default_factory=list)


def _default_config_path() -> Path:
    return Path(__file__).with_name("default_capabilities.json")


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise internal_error(
            message="YAML config support requires PyYAML",
            data={"path": str(path)},
        ) from exc

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _load_config_data(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return _load_yaml(path)

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_capability_config() -> MCPCapabilityConfig:
    """Load and validate MCP capability config from disk."""
    config_path = Path(settings.MCP_CONFIG_PATH) if settings.MCP_CONFIG_PATH else _default_config_path()
    if not config_path.is_absolute():
        config_path = (Path(__file__).resolve().parents[3] / config_path).resolve()

    if not config_path.exists():
        raise internal_error(
            message="MCP capability config file does not exist",
            data={"path": str(config_path)},
        )

    data = _load_config_data(config_path)
    return MCPCapabilityConfig.model_validate(data)