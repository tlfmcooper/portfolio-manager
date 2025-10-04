"""Redis Client for Caching"""
import json
import redis
from typing import Any, Optional
from app.core.config import settings


class RedisClient:
    """Redis client for caching operations"""

    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with optional TTL"""
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                return self.client.setex(key, ttl, serialized)
            return self.client.set(key, serialized)
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False

    def lpush(self, key: str, *values: Any) -> int:
        """Push values to list"""
        try:
            serialized = [json.dumps(v, default=str) for v in values]
            return self.client.lpush(key, *serialized)
        except Exception as e:
            print(f"Redis LPUSH error: {e}")
            return 0

    def lrange(self, key: str, start: int = 0, end: int = -1) -> list:
        """Get range from list"""
        try:
            values = self.client.lrange(key, start, end)
            return [json.loads(v) for v in values]
        except Exception as e:
            print(f"Redis LRANGE error: {e}")
            return []


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get or create Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
