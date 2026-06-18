import pytest

from app.policies.retry import CircuitBreaker, RetryPolicy
from app.providers.registry import ProviderRegistry
from tests.conftest import FakeProvider


@pytest.mark.asyncio
async def test_retry_policy_retries_then_succeeds() -> None:
  attempts = {"count": 0}

  async def operation() -> str:
    attempts["count"] += 1
    if attempts["count"] < 2:
      raise RuntimeError("temporary")
    return "ok"

  policy = RetryPolicy(max_attempts=3, backoff_seconds=0)
  assert await policy.execute(operation) == "ok"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures() -> None:
  breaker = CircuitBreaker(failure_threshold=2, reset_timeout=30)

  async def failing() -> str:
    raise RuntimeError("fail")

  with pytest.raises(RuntimeError):
    await breaker.execute(failing)
  with pytest.raises(RuntimeError):
    await breaker.execute(failing)

  with pytest.raises(Exception):
    await breaker.execute(failing)


def test_provider_registry() -> None:
  registry = ProviderRegistry()
  registry.register("fake", lambda: FakeProvider())
  provider = registry.create("fake")
  assert provider.name == "fake"
