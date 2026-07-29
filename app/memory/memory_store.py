from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings


class ConversationMemoryStore(ABC):
    """Conversation memory persistence interface."""

    @abstractmethod
    async def append(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session."""

    @abstractmethod
    async def get_history(
        self,
        session_id: str,
        limit: int | None = None,
        max_chars: int | None = None,
    ) -> list[dict[str, str]]:
        """Return recent session history."""

    @abstractmethod
    async def clear(self, session_id: str) -> None:
        """Clear a session."""

    @abstractmethod
    async def summary(self, session_id: str) -> dict[str, Any]:
        """Return session summary metadata."""

    def _trim_by_chars(
        self, messages: list[dict[str, str]], max_chars: int
    ) -> list[dict[str, str]]:
        """Keep the most recent messages that fit within a character budget."""
        selected: list[dict[str, str]] = []
        total_chars = 0
        for message in reversed(messages):
            content_length = len(message["content"])
            if selected and total_chars + content_length > max_chars:
                break
            selected.append(message)
            total_chars += content_length
        selected.reverse()
        return selected

    def _apply_limits(
        self,
        messages: list[dict[str, str]],
        limit: int | None,
        max_chars: int | None,
    ) -> list[dict[str, str]]:
        message_limit = limit or settings.MEMORY_MAX_MESSAGES
        char_limit = max_chars or settings.MEMORY_MAX_CHARS
        trimmed = messages[-message_limit:]
        return self._trim_by_chars(trimmed, char_limit)
