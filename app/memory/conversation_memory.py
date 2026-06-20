from typing import Any

from app.memory.memory_store import ConversationMemoryStore


class InMemoryConversationMemory(ConversationMemoryStore):
    """In-memory session-scoped conversation memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, str]]] = {}

    async def append(self, session_id: str, role: str, content: str) -> None:
        self._sessions.setdefault(session_id, []).append({"role": role, "content": content})

    async def get_history(
        self,
        session_id: str,
        limit: int | None = None,
        max_chars: int | None = None,
    ) -> list[dict[str, str]]:
        messages = list(self._sessions.get(session_id, []))
        if not messages:
            return []
        return self._apply_limits(messages, limit, max_chars)

    async def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    async def summary(self, session_id: str) -> dict[str, Any]:
        history = self._sessions.get(session_id, [])
        return {"session_id": session_id, "message_count": len(history)}
