"""Structured logging helpers for MCP traffic."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger("app.mcp")

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}

_minimum_client_log_level = "warning"


def set_client_log_level(level: str) -> str:
    """Set the minimum client-facing log level for SSE notifications."""
    global _minimum_client_log_level
    normalized = level.strip().lower()
    if normalized not in LOG_LEVELS:
        raise ValueError(f"Unsupported log level: {level}")
    _minimum_client_log_level = normalized
    return _minimum_client_log_level


def get_client_log_level() -> str:
    return _minimum_client_log_level


def should_emit_client_log(level: str) -> bool:
    normalized = level.strip().lower()
    if normalized not in LOG_LEVELS:
        return False
    return LOG_LEVELS[normalized] >= LOG_LEVELS[_minimum_client_log_level]


def log_event(level: int, event: str, **fields: Any) -> None:
    """Emit a structured log line as JSON."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.log(level, json.dumps(payload, default=str))