import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import settings
from app.core.exceptions import CircuitBreakerOpenException

T = TypeVar("T")


class RetryPolicy:
    """Retry transient failures with exponential backoff."""

    def __init__(
        self,
        max_attempts: int | None = None,
        backoff_seconds: float | None = None,
    ) -> None:
        self._max_attempts = max_attempts or settings.RETRY_MAX_ATTEMPTS
        self._backoff_seconds = backoff_seconds or settings.RETRY_BACKOFF_SECONDS

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute an async operation with retries."""
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await operation()
            except Exception as exc:
                last_error = exc
                if attempt == self._max_attempts:
                    break
                await asyncio.sleep(self._backoff_seconds * attempt)
        raise last_error or RuntimeError("Retry policy failed without an exception")


class TimeoutPolicy:
    """Enforce request timeouts."""

    def __init__(self, timeout_seconds: float | None = None) -> None:
        self._timeout_seconds = timeout_seconds or settings.REQUEST_TIMEOUT_SECONDS

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute an async operation with a timeout."""
        return await asyncio.wait_for(operation(), timeout=self._timeout_seconds)


class CircuitBreaker:
    """Protect downstream dependencies from cascading failures."""

    def __init__(
        self,
        failure_threshold: int | None = None,
        reset_timeout: float | None = None,
    ) -> None:
        self._failure_threshold = failure_threshold or settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self._reset_timeout = reset_timeout or settings.CIRCUIT_BREAKER_RESET_TIMEOUT
        self._failure_count = 0
        self._opened_at: float | None = None

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute an operation guarded by the circuit breaker."""
        if self._is_open():
            raise CircuitBreakerOpenException()
        try:
            result = await operation()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self._reset_timeout:
            self._failure_count = 0
            self._opened_at = None
            return False
        return True

    def _on_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None

    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._opened_at = time.monotonic()
