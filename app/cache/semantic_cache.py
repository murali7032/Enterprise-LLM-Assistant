from abc import ABC, abstractmethod
from typing import Any


class SemanticCacheInterface(ABC):
    """Semantic cache abstraction."""

    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a cached value."""

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        """Store a value in the cache."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a cached value."""
