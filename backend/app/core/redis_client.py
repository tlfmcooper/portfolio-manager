"""
Redis Client for Caching
"""
import json
from typing import Any, Optional
import redis.asyncio as redis
from app.core.config import settings


class RedisClient:
    """Async Redis client wrapper"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = await redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            encoding="utf-8",
            decode_responses=True
        )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.redis:
            return None
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with optional TTL"""
        if not self.redis:
            return False

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if ttl:
            return await self.redis.setex(key, ttl, value)
        return await self.redis.set(key, value)

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis:
            return False
        return await self.redis.delete(key) > 0

    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to list"""
        if not self.redis:
            return 0
        serialized = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in values]
        return await self.redis.lpush(key, *serialized)

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> list:
        """Get range from list"""
        if not self.redis:
            return []
        values = await self.redis.lrange(key, start, end)
        return [json.loads(v) if v.startswith('{') or v.startswith('[') else v for v in values]

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False
        return await self.redis.exists(key) > 0


# Global Redis client instance
_redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    """Get Redis client instance"""
    return _redis_client
