"""Server-side session store (opaque session id → user payload)."""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from app.clients.redis_client import RedisClient
from app.core.config import settings


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


class SessionStore(ABC):
    """Persist browser auth sessions."""

    @abstractmethod
    async def create(self, data: dict[str, Any], ttl_seconds: int | None = None) -> str:
        """Create a session and return its id."""

    @abstractmethod
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Load session data by id."""

    @abstractmethod
    async def touch(self, session_id: str, ttl_seconds: int | None = None) -> None:
        """Refresh TTL (sliding expiry)."""

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Destroy a session."""

    @abstractmethod
    async def delete_all_for_user(self, user_id: str) -> int:
        """Revoke every session for a user. Returns count deleted."""

    @abstractmethod
    async def set_oauth_state(
        self, state: str, payload: dict[str, Any], ttl_seconds: int | None = None
    ) -> None:
        """Store OAuth CSRF state."""

    @abstractmethod
    async def pop_oauth_state(self, state: str) -> dict[str, Any] | None:
        """Consume OAuth state (one-time)."""


class InMemorySessionStore(SessionStore):
    """Process-local sessions for tests and single-node local dev."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._user_index: dict[str, set[str]] = {}
        self._oauth_states: dict[str, dict[str, Any]] = {}

    async def create(self, data: dict[str, Any], ttl_seconds: int | None = None) -> str:
        session_id = new_session_id()
        payload = {
            **data,
            "created_at": datetime.now(UTC).isoformat(),
            "_ttl": ttl_seconds or settings.SESSION_TTL_SECONDS,
        }
        self._sessions[session_id] = payload
        user_id = str(data.get("user_id", ""))
        if user_id:
            self._user_index.setdefault(user_id, set()).add(session_id)
        return session_id

    async def get(self, session_id: str) -> dict[str, Any] | None:
        data = self._sessions.get(session_id)
        if data is None:
            return None
        return {k: v for k, v in data.items() if not k.startswith("_")}

    async def touch(self, session_id: str, ttl_seconds: int | None = None) -> None:
        data = self._sessions.get(session_id)
        if data is not None:
            data["_ttl"] = ttl_seconds or settings.SESSION_TTL_SECONDS

    async def delete(self, session_id: str) -> None:
        data = self._sessions.pop(session_id, None)
        if data is None:
            return
        user_id = str(data.get("user_id", ""))
        if user_id in self._user_index:
            self._user_index[user_id].discard(session_id)

    async def delete_all_for_user(self, user_id: str) -> int:
        ids = list(self._user_index.get(user_id, set()))
        for session_id in ids:
            await self.delete(session_id)
        return len(ids)

    async def set_oauth_state(
        self, state: str, payload: dict[str, Any], ttl_seconds: int | None = None
    ) -> None:
        self._oauth_states[state] = {
            **payload,
            "_ttl": ttl_seconds or settings.OAUTH_STATE_TTL_SECONDS,
        }

    async def pop_oauth_state(self, state: str) -> dict[str, Any] | None:
        data = self._oauth_states.pop(state, None)
        if data is None:
            return None
        return {k: v for k, v in data.items() if not k.startswith("_")}


class RedisSessionStore(SessionStore):
    """Redis-backed sessions suitable for multi-replica deployments."""

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _user_key(self, user_id: str) -> str:
        return f"session_user:{user_id}"

    def _oauth_key(self, state: str) -> str:
        return f"oauth_state:{state}"

    async def create(self, data: dict[str, Any], ttl_seconds: int | None = None) -> str:
        session_id = new_session_id()
        ttl = ttl_seconds or settings.SESSION_TTL_SECONDS
        payload = {**data, "created_at": datetime.now(UTC).isoformat()}
        await self._redis.set_json(self._key(session_id), payload, ttl_seconds=ttl)
        user_id = str(data.get("user_id", ""))
        if user_id:
            await self._redis.sadd(self._user_key(user_id), session_id)
            await self._redis.expire(self._user_key(user_id), ttl)
        return session_id

    async def get(self, session_id: str) -> dict[str, Any] | None:
        return await self._redis.get_json(self._key(session_id))

    async def touch(self, session_id: str, ttl_seconds: int | None = None) -> None:
        data = await self.get(session_id)
        if data is None:
            return
        ttl = ttl_seconds or settings.SESSION_TTL_SECONDS
        await self._redis.set_json(self._key(session_id), data, ttl_seconds=ttl)

    async def delete(self, session_id: str) -> None:
        data = await self.get(session_id)
        await self._redis.delete(self._key(session_id))
        if data and data.get("user_id"):
            await self._redis.srem(self._user_key(str(data["user_id"])), session_id)

    async def delete_all_for_user(self, user_id: str) -> int:
        session_ids = await self._redis.smembers(self._user_key(user_id))
        count = 0
        for session_id in session_ids:
            await self.delete(session_id)
            count += 1
        await self._redis.delete(self._user_key(user_id))
        return count

    async def set_oauth_state(
        self, state: str, payload: dict[str, Any], ttl_seconds: int | None = None
    ) -> None:
        ttl = ttl_seconds or settings.OAUTH_STATE_TTL_SECONDS
        await self._redis.set_json(self._oauth_key(state), payload, ttl_seconds=ttl)

    async def pop_oauth_state(self, state: str) -> dict[str, Any] | None:
        data = await self._redis.get_json(self._oauth_key(state))
        await self._redis.delete(self._oauth_key(state))
        return data
