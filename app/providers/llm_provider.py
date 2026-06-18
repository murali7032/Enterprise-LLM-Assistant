from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.models.llm_response import LLMResult


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""

    @abstractmethod
    async def generate(self, prompt: str) -> LLMResult:
        """Generate a completion for the given prompt."""

    @abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream a completion for the given prompt."""
