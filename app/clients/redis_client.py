from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings


class RedisClient:
    """Thin wrapper around the Redis SDK."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.REDIS_URL
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Establish the Redis connection."""
        if self._client is None:
            self._client = redis.from_url(self._url, decode_responses=True)

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        await self.connect()
        assert self._client is not None
        return bool(await self._client.ping())

    async def get(self, key: str) -> str | None:
        """Get a string value."""
        await self.connect()
        assert self._client is not None
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """Set a string value with optional TTL."""
        await self.connect()
        assert self._client is not None
        await self._client.set(key, value, ex=ttl_seconds)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Get and deserialize a JSON value."""
        raw = await self.get(key)
        return json.loads(raw) if raw else None

    async def set_json(
        self, key: str, value: dict[str, Any], ttl_seconds: int | None = None
    ) -> None:
        """Serialize and store a JSON value."""
        await self.set(key, json.dumps(value), ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> None:
        """Delete a key."""
        await self.connect()
        assert self._client is not None
        await self._client.delete(key)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        """Set key expiry in seconds."""
        await self.connect()
        assert self._client is not None
        await self._client.expire(key, ttl_seconds)

    async def sadd(self, key: str, *members: str) -> None:
        """Add members to a Redis set."""
        await self.connect()
        assert self._client is not None
        if members:
            await self._client.sadd(key, *members)

    async def srem(self, key: str, *members: str) -> None:
        """Remove members from a Redis set."""
        await self.connect()
        assert self._client is not None
        if members:
            await self._client.srem(key, *members)

    async def smembers(self, key: str) -> set[str]:
        """Return all members of a Redis set."""
        await self.connect()
        assert self._client is not None
        members = await self._client.smembers(key)
        return set(members or [])

    async def incr(self, key: str) -> int:
        """Increment an integer counter."""
        await self.connect()
        assert self._client is not None
        return int(await self._client.incr(key))
