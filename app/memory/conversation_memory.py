from typing import Any


class ConversationMemory:
    """Session-scoped conversation memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, str]]] = {}

    def append(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session."""
        self._sessions.setdefault(session_id, []).append({"role": role, "content": content})

    def get_history(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Return recent session history."""
        return self._sessions.get(session_id, [])[-limit:]

    def clear(self, session_id: str) -> None:
        """Clear a session."""
        self._sessions.pop(session_id, None)

    def summary(self, session_id: str) -> dict[str, Any]:
        """Return session summary metadata."""
        history = self._sessions.get(session_id, [])
        return {"session_id": session_id, "message_count": len(history)}
