"""In-memory session state for MCP Streamable HTTP support."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from typing import Any, Optional
from uuid import uuid4


@dataclass(slots=True)
class StreamState:
    stream_id: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    counter: Any = field(default_factory=lambda: count(1))

    def next_event_id(self) -> str:
        return f"{self.stream_id}:{next(self.counter)}"


@dataclass(slots=True)
class SessionState:
    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    initialized: bool = False
    protocol_version: Optional[str] = None
    client_info: dict[str, Any] = field(default_factory=dict)
    client_capabilities: dict[str, Any] = field(default_factory=dict)
    subscriptions: set[str] = field(default_factory=set)
    streams: OrderedDict[str, StreamState] = field(default_factory=OrderedDict)


class MCPSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> SessionState:
        async with self._lock:
            session = SessionState(session_id=str(uuid4()))
            self._sessions[session.session_id] = session
            return session

    async def get_session(self, session_id: str | None) -> SessionState | None:
        if not session_id:
            return None
        async with self._lock:
            return self._sessions.get(session_id)

    async def get_or_create_session(self, session_id: str | None = None) -> SessionState:
        existing = await self.get_session(session_id)
        if existing:
            return existing
        return await self.create_session()

    async def initialize_session(
        self,
        session: SessionState,
        protocol_version: str,
        client_info: dict[str, Any],
        client_capabilities: dict[str, Any],
    ) -> SessionState:
        async with self._lock:
            session.initialized = True
            session.protocol_version = protocol_version
            session.client_info = client_info
            session.client_capabilities = client_capabilities
            return session

    async def delete_session(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None

    async def add_subscription(self, session_id: str, uri: str) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.subscriptions.add(uri)

    async def remove_subscription(self, session_id: str, uri: str) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.subscriptions.discard(uri)

    async def attach_stream(self, session_id: str) -> tuple[SessionState, StreamState]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session = SessionState(session_id=session_id)
                self._sessions[session_id] = session
            stream = StreamState(stream_id=str(uuid4()))
            session.streams[stream.stream_id] = stream
            return session, stream

    async def detach_stream(self, session_id: str, stream_id: str) -> None:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.streams.pop(stream_id, None)

    async def publish(self, session_id: str | None, message: dict[str, Any]) -> bool:
        if not session_id:
            return False
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session or not session.streams:
                return False
            stream = next(iter(session.streams.values()))
            payload = {"event_id": stream.next_event_id(), "payload": message}
            await stream.queue.put(payload)
            return True

    async def publish_to_subscribers(self, uri: str, message: dict[str, Any]) -> int:
        async with self._lock:
            streams = [next(iter(session.streams.values())) for session in self._sessions.values() if uri in session.subscriptions and session.streams]

        for stream in streams:
            await stream.queue.put({"event_id": stream.next_event_id(), "payload": message})

        return len(streams)


session_store = MCPSessionStore()