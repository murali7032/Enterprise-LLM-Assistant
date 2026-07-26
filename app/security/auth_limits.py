"""Auth rate limiting and login lockout helpers."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException

from app.clients.redis_client import RedisClient
from app.core.config import settings


class AuthRateLimiter:
    """Per-key rate limits for auth endpoints (memory or Redis)."""

    def __init__(self, redis_client: RedisClient | None = None) -> None:
        self._redis = redis_client
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)

    async def check(self, key: str) -> None:
        window = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
        limit = settings.AUTH_RATE_LIMIT_REQUESTS
        if self._redis is not None and settings.SESSION_BACKEND == "redis":
            redis_key = f"auth_rl:{key}"
            count = await self._redis.incr(redis_key)
            if count == 1:
                await self._redis.expire(redis_key, window)
            if count > limit:
                raise HTTPException(status_code=429, detail="Too many auth attempts")
            return

        now = time.monotonic()
        bucket = self._buckets[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="Too many auth attempts")
        bucket.append(now)


class LoginLockoutStore:
    """Track failed password attempts and temporary lockouts."""

    def __init__(self, redis_client: RedisClient | None = None) -> None:
        self._redis = redis_client
        self._failures: dict[str, int] = {}
        self._locked_until: dict[str, float] = {}

    async def assert_not_locked(self, email: str) -> None:
        key = email.strip().lower()
        if self._redis is not None and settings.SESSION_BACKEND == "redis":
            locked = await self._redis.get(f"auth_lock:{key}")
            if locked:
                raise HTTPException(status_code=423, detail="Account temporarily locked")
            return
        until = self._locked_until.get(key)
        if until and until > time.monotonic():
            raise HTTPException(status_code=423, detail="Account temporarily locked")
        if until:
            self._locked_until.pop(key, None)
            self._failures.pop(key, None)

    async def record_failure(self, email: str) -> None:
        key = email.strip().lower()
        if self._redis is not None and settings.SESSION_BACKEND == "redis":
            fail_key = f"auth_fail:{key}"
            count = await self._redis.incr(fail_key)
            if count == 1:
                await self._redis.expire(fail_key, settings.AUTH_LOCKOUT_SECONDS)
            if count >= settings.AUTH_LOGIN_MAX_FAILURES:
                await self._redis.set(f"auth_lock:{key}", "1", ttl_seconds=settings.AUTH_LOCKOUT_SECONDS)
            return

        self._failures[key] = self._failures.get(key, 0) + 1
        if self._failures[key] >= settings.AUTH_LOGIN_MAX_FAILURES:
            self._locked_until[key] = time.monotonic() + settings.AUTH_LOCKOUT_SECONDS
            self._failures[key] = 0

    async def clear_failures(self, email: str) -> None:
        key = email.strip().lower()
        if self._redis is not None and settings.SESSION_BACKEND == "redis":
            await self._redis.delete(f"auth_fail:{key}")
            await self._redis.delete(f"auth_lock:{key}")
            return
        self._failures.pop(key, None)
        self._locked_until.pop(key, None)
