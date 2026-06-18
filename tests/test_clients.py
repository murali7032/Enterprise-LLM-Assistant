import pytest
from unittest.mock import AsyncMock, MagicMock

from app.clients.redis_client import RedisClient
from app.dependencies import get_provider_registry
from app.providers.gemini_provider import GeminiProvider
from app.services.llm_service import LLMService
from tests.conftest import FakeProvider


@pytest.mark.asyncio
async def test_redis_client_json_roundtrip(monkeypatch) -> None:
  store: dict[str, str] = {}

  class FakeRedis:
    async def ping(self):
      return True

    async def get(self, key):
      return store.get(key)

    async def set(self, key, value, ex=None):
      store[key] = value

    async def delete(self, key):
      store.pop(key, None)

    async def close(self):
      return None

  monkeypatch.setattr("app.clients.redis_client.redis.from_url", lambda *_a, **_k: FakeRedis())
  client = RedisClient()
  await client.set_json("k", {"a": 1}, ttl_seconds=10)
  assert await client.get_json("k") == {"a": 1}


@pytest.mark.asyncio
async def test_gemini_provider_with_mock_client() -> None:
  mock_client = MagicMock()
  mock_client.generate = AsyncMock(
    return_value={
      "content": "gemini",
      "model": "gemini",
      "prompt_tokens": 1,
      "completion_tokens": 1,
      "total_tokens": 2,
    }
  )
  mock_client.stream = AsyncMock()

  async def _stream(**_kwargs):
    yield "x"

  mock_client.stream.side_effect = _stream
  provider = GeminiProvider(client=mock_client)
  result = await provider.generate("hello")
  assert result.content == "gemini"


def test_provider_registry_from_dependencies() -> None:
  registry = get_provider_registry()
  assert "openai" in registry.supported_providers()


@pytest.mark.asyncio
async def test_llm_service_stream() -> None:
  service = LLMService(provider=FakeProvider(), cache=None)
  chunks = []
  async for chunk in service.stream("hello"):
    chunks.append(chunk)
  assert chunks == ["chunk"]
