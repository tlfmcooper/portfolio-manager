"""
Redis client for caching market data.
"""

import json
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

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            await self.redis.ping()
            self.connected = True
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Running without cache.")
            self.connected = False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self.connected or not self.redis:
            return None
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in Redis with optional TTL."""
        if not self.connected or not self.redis:
            return
        try:
            serialized = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")

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
        """Delete key from Redis."""
        if not self.connected or not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.connected or not self.redis:
            return False
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
        await _redis_client.connect()
    return _redis_client
