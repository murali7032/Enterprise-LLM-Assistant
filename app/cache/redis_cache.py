from typing import Any

from app.cache.cache_key import build_cache_key
from app.cache.semantic_cache import SemanticCacheInterface
from app.clients.redis_client import RedisClient
from app.core.config import settings


class RedisSemanticCache(SemanticCacheInterface):
    """Redis-backed semantic cache implementation."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    async def get(self, key: str) -> dict[str, Any] | None:
        return await self._redis_client.get_json(key)

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        await self._redis_client.set_json(key, value, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis_client.delete(key)

    def build_llm_key(self, provider: str, model: str, prompt: str) -> str:
        """Build a cache key for LLM responses."""
        return build_cache_key(
            namespace="llm",
            payload={
                "provider": provider,
                "model": model,
                "prompt": prompt,
            },
        )

    @property
    def default_ttl(self) -> int:
        return settings.CACHE_TTL_SECONDS
