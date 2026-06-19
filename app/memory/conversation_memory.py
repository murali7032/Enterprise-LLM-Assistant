from typing import Any

from app.core.config import settings


class ConversationMemory:
    """Session-scoped conversation memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, str]]] = {}

    def append(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session."""
        self._sessions.setdefault(session_id, []).append({"role": role, "content": content})

    def get_history(
        self,
        session_id: str,
        limit: int | None = None,
        max_chars: int | None = None,
    ) -> list[dict[str, str]]:
        """Return recent session history within message and character limits."""
        messages = list(self._sessions.get(session_id, []))
        if not messages:
            return []

        message_limit = limit or settings.MEMORY_MAX_MESSAGES
        char_limit = max_chars or settings.MEMORY_MAX_CHARS

        trimmed = messages[-message_limit:]
        return self._trim_by_chars(trimmed, char_limit)

    def _trim_by_chars(self, messages: list[dict[str, str]], max_chars: int) -> list[dict[str, str]]:
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

    def clear(self, session_id: str) -> None:
        """Clear a session."""
        self._sessions.pop(session_id, None)

    def summary(self, session_id: str) -> dict[str, Any]:
        """Return session summary metadata."""
        history = self._sessions.get(session_id, [])
        return {"session_id": session_id, "message_count": len(history)}
