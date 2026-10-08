"""
Redis client for caching market data.
"""

import json
import asyncio
from collections import OrderedDict
from time import monotonic
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for caching operations."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.connected = False
        self._memory = OrderedDict()
        self._loads = {}
        self._generation = 0
        self._retry_at = 0.0
        self._connect_lock = asyncio.Lock()
        self._dirty_keys = set()
        self._dirty_prefixes = set()

    async def connect(self):
        """Connect to Redis."""
        try:
            if self.redis:
                await self.redis.aclose()
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            # Test connection
            await self.redis.ping()
            # Replay invalidations made while Redis was unavailable before reading it.
            for prefix in list(self._dirty_prefixes):
                async for key in self.redis.scan_iter(match=prefix + "*", count=100):
                    await self.redis.delete(key)
                self._dirty_prefixes.discard(prefix)
            for key in list(self._dirty_keys):
                await self.redis.delete(key)
                self._dirty_keys.discard(key)
            self.connected = True
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            self.connected = False
            self._retry_at = monotonic() + 30

    async def ensure_connected(self):
        if self.connected or monotonic() < self._retry_at:
            return
        async with self._connect_lock:
            if not self.connected and monotonic() >= self._retry_at:
                await self.connect()

    def _remote_failed(self):
        self.connected = False
        self._retry_at = monotonic() + 30

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("Redis disconnected")

    def _remember(self, key, serialized, ttl):
        self._memory[key] = (monotonic() + ttl if ttl else float("inf"), serialized)
        self._memory.move_to_end(key)
        while len(self._memory) > 512:
            self._memory.popitem(last=False)

    def _memory_get(self, key):
        entry = self._memory.get(key)
        if entry is None:
            return None
        if entry[0] <= monotonic():
            del self._memory[key]
            return None
        self._memory.move_to_end(key)
        return json.loads(entry[1])

    async def get(self, key: str) -> Optional[Any]:
        """Use a bounded TTL cache when Redis is unavailable."""
        if self.connected and self.redis:
            try:
                value = await self.redis.get(key)
                return json.loads(value) if value else None
            except Exception as e:
                self._remote_failed()
                logger.warning("Redis GET failed; using local cache: %s", e)
        return self._memory_get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        serialized = json.dumps(value, default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v))
        self._remember(key, serialized, ttl)
        self._dirty_keys.add(key)
        if self.connected and self.redis:
            try:
                if ttl:
                    await self.redis.setex(key, ttl, serialized)
                else:
                    await self.redis.set(key, serialized)
                self._dirty_keys.discard(key)
            except Exception as e:
                self._remote_failed()
                logger.warning("Redis SET failed; using local cache: %s", e)

    async def get_or_load(self, key, loader, ttl):
        """Coalesce concurrent misses without sharing request database sessions."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        entry = self._loads.setdefault(key, [asyncio.Lock(), 0])
        entry[1] += 1
        try:
            async with entry[0]:
                cached = await self.get(key)
                if cached is not None:
                    return cached
                generation = self._generation
                data = await loader()
                if generation == self._generation and not (isinstance(data, dict) and data.get("error")):
                    await self.set(key, data, ttl=ttl)
                return data
        finally:
            entry[1] -= 1
            if entry[1] == 0:
                self._loads.pop(key, None)

    async def delete_prefix(self, prefix):
        self._generation += 1
        self._dirty_prefixes.add(prefix)
        for key in list(self._memory):
            if key.startswith(prefix):
                del self._memory[key]
        if self.connected and self.redis:
            try:
                async for key in self.redis.scan_iter(match=prefix + "*", count=100):
                    await self.redis.delete(key)
                self._dirty_prefixes.discard(prefix)
            except Exception as e:
                self._remote_failed()
                logger.warning("Redis invalidation failed: %s", e)

    async def setex(self, key: str, ttl: int, value: Any):
        """Set value in Redis with TTL (alias for set with ttl)."""
        await self.set(key, value, ttl=ttl)

    async def lpush(self, key: str, value: Any, max_length: int = 1000):
        """Push value to list and trim to max length."""
        if not self.connected or not self.redis:
            return
        try:
            serialized = json.dumps(value)
            await self.redis.lpush(key, serialized)
            await self.redis.ltrim(key, 0, max_length - 1)
        except Exception as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from list."""
        if not self.connected or not self.redis:
            return []
        try:
            values = await self.redis.lrange(key, start, end)
            return [json.loads(v) for v in values]
        except Exception as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []

    async def delete(self, key: str):
        """Invalidate both distributed and local cache entries."""
        self._generation += 1
        self._memory.pop(key, None)
        self._dirty_keys.add(key)
        if self.connected and self.redis:
            try:
                await self.redis.delete(key)
                self._dirty_keys.discard(key)
            except Exception as e:
                self._remote_failed()
                logger.warning("Redis DELETE error for %s: %s", key, e)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.connected or not self.redis:
            return self._memory_get(key) is not None
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False


# Singleton instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    await _redis_client.ensure_connected()
    return _redis_client
