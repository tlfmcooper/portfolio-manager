"""Strict, per-user encrypted storage, independent of the best-effort cache."""

import json

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class ChatSecrets:
    def __init__(self, redis: Redis, encryption_key: str):
        try:
            self.cipher = Fernet(encryption_key.encode("ascii"))
        except (ValueError, UnicodeError):
            raise HTTPException(503, "Chat secret encryption is not configured.") from None
        self.redis = redis

    @staticmethod
    def storage_key(user_id: int) -> str:
        return f"secrets:chat:gemini:{user_id}"

    async def read(self, user_id: int) -> str | None:
        try:
            token = await self.redis.get(self.storage_key(user_id))
        except RedisError:
            raise HTTPException(503, "Chat secret storage is unavailable.") from None
        if token is None:
            return None
        try:
            payload = json.loads(self.cipher.decrypt(token.encode() if isinstance(token, str) else token))
            if payload["user_id"] != user_id or payload["provider"] != "gemini":
                raise ValueError("Identity mismatch")
            if not isinstance(payload["api_key"], str) or not payload["api_key"]:
                raise ValueError("Invalid secret")
            return payload["api_key"]
        except (InvalidToken, ValueError, KeyError, TypeError, UnicodeError):
            raise HTTPException(503, "Saved chat key cannot be decrypted. Restore the encryption configuration or replace the key.") from None

    async def save(self, user_id: int, api_key: str) -> None:
        token = self.cipher.encrypt(json.dumps({
            "user_id": user_id, "provider": "gemini", "api_key": api_key,
        }).encode())
        try:
            # SET without expiration also removes any TTL left by an older value.
            saved = await self.redis.set(self.storage_key(user_id), token)
            if not saved:
                raise RedisError("Write was not acknowledged")
        except RedisError:
            raise HTTPException(503, "Chat key could not be saved. Please try again.") from None

    async def delete(self, user_id: int) -> None:
        try:
            await self.redis.delete(self.storage_key(user_id))
        except RedisError:
            raise HTTPException(503, "Chat key could not be removed. Please try again.") from None


async def get_chat_secrets():
    try:
        client = Redis.from_url(
            settings.CHAT_SECRETS_REDIS_URL or settings.REDIS_URL,
            socket_connect_timeout=5, socket_timeout=5,
        )
    except ValueError:
        raise HTTPException(503, "Chat secret storage is not configured correctly.") from None
    try:
        yield ChatSecrets(client, settings.CHAT_SECRET_ENCRYPTION_KEY)
    finally:
        await client.aclose()
