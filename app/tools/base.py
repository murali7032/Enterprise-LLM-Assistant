from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract tool interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the tool description."""

    @abstractmethod
    async def execute(self, query: str) -> dict[str, Any]:
        """Execute the tool with the given query."""
