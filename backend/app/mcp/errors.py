"""MCP error types and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class MCPError(Exception):
    """Base exception for MCP transport and protocol errors."""

    code: int
    message: str
    data: Optional[Any] = None
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


def parse_error(message: str = "Parse error", data: Any = None) -> MCPError:
    return MCPError(code=-32700, message=message, data=data, status_code=400)


def invalid_request(message: str = "Invalid Request", data: Any = None) -> MCPError:
    return MCPError(code=-32600, message=message, data=data, status_code=400)


def method_not_found(message: str = "Method not found", data: Any = None) -> MCPError:
    return MCPError(code=-32601, message=message, data=data, status_code=404)


def invalid_params(message: str = "Invalid params", data: Any = None) -> MCPError:
    return MCPError(code=-32602, message=message, data=data, status_code=422)


def internal_error(message: str = "Internal error", data: Any = None) -> MCPError:
    return MCPError(code=-32603, message=message, data=data, status_code=500)


def unauthorized(message: str = "Authentication required", data: Any = None) -> MCPError:
    return MCPError(code=-32001, message=message, data=data, status_code=401)


def forbidden(message: str = "Forbidden", data: Any = None) -> MCPError:
    return MCPError(code=-32003, message=message, data=data, status_code=403)


def not_found(message: str = "Not found", data: Any = None) -> MCPError:
    return MCPError(code=-32004, message=message, data=data, status_code=404)


def upstream_error(message: str = "Upstream service failed", data: Any = None) -> MCPError:
    return MCPError(code=-32050, message=message, data=data, status_code=502)