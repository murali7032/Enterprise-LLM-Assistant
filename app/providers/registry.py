from collections.abc import Callable

from app.core.exceptions import LLMProviderException
from app.providers.llm_provider import LLMProvider


class ProviderRegistry:
    """Registry/factory for LLM providers."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], LLMProvider]] = {}

    def register(self, name: str, factory: Callable[[], LLMProvider]) -> None:
        """Register a provider factory."""
        self._factories[name.lower()] = factory

    def create(self, name: str) -> LLMProvider:
        """Create a provider by name."""
        factory = self._factories.get(name.lower())
        if factory is None:
            raise LLMProviderException(f"Unsupported LLM provider: {name}")
        return factory()

    def supported_providers(self) -> list[str]:
        """Return registered provider names."""
        return sorted(self._factories.keys())
