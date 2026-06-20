from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessageRecord, ChatSessionRecord
from app.memory.memory_store import ConversationMemoryStore


class PostgresConversationMemory(ConversationMemoryStore):
    """PostgreSQL-backed conversation memory."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, session_id: str, role: str, content: str) -> None:
        existing = await self._session.execute(
            select(ChatSessionRecord).where(ChatSessionRecord.session_id == session_id)
        )
        if existing.scalar_one_or_none() is None:
            self._session.add(ChatSessionRecord(session_id=session_id))

        self._session.add(
            ChatMessageRecord(session_id=session_id, role=role, content=content)
        )
        await self._session.commit()

    async def get_history(
        self,
        session_id: str,
        limit: int | None = None,
        max_chars: int | None = None,
    ) -> list[dict[str, str]]:
        message_limit = limit or 100
        result = await self._session.execute(
            select(ChatMessageRecord)
            .where(ChatMessageRecord.session_id == session_id)
            .order_by(ChatMessageRecord.created_at.desc())
            .limit(message_limit)
        )
        records = list(reversed(result.scalars().all()))
        messages = [{"role": record.role, "content": record.content} for record in records]
        return self._apply_limits(messages, limit, max_chars)

    async def clear(self, session_id: str) -> None:
        await self._session.execute(
            delete(ChatMessageRecord).where(ChatMessageRecord.session_id == session_id)
        )
        await self._session.execute(
            delete(ChatSessionRecord).where(ChatSessionRecord.session_id == session_id)
        )
        await self._session.commit()

    async def summary(self, session_id: str) -> dict[str, Any]:
        result = await self._session.execute(
            select(func.count())
            .select_from(ChatMessageRecord)
            .where(ChatMessageRecord.session_id == session_id)
        )
        count = result.scalar_one()
        return {"session_id": session_id, "message_count": count}
