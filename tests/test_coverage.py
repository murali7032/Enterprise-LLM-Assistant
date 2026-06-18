import pytest

from app.core.exceptions import AppException, AuthorizationException
from app.parser.output_parser import OutputParser
from app.providers.openai_provider import OpenAIProvider
from app.security.authentication import require_permission
from app.services.llm_service import LLMService
from tests.conftest import FakeProvider


def test_output_parser_fenced_json() -> None:
  parser = OutputParser()
  result = parser.parse_json('```json\n{"action": "finish"}\n```')
  assert result["action"] == "finish"


def test_output_parser_invalid_json() -> None:
  parser = OutputParser()
  with pytest.raises(AppException):
    parser.parse_json("not-json")


def test_output_parser_tool_response() -> None:
  parser = OutputParser()
  result = parser.parse_tool_response('{"action": "weather", "input": "London"}')
  assert result["action"] == "weather"


def test_require_permission_denied() -> None:
  with pytest.raises(AuthorizationException):
    require_permission("viewer", "agents")


@pytest.mark.asyncio
async def test_llm_service_cache_hit(monkeypatch) -> None:
  class Cache:
    def build_llm_key(self, *_args):
      return "k"

    @property
    def default_ttl(self):
      return 60

    async def get(self, _key):
      return {
        "content": "cached",
        "model": "fake",
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2,
        "cost_usd": 0.0,
      }

    async def set(self, *_args, **_kwargs):
      return None

  service = LLMService(provider=FakeProvider(), cache=Cache())
  result = await service.generate("hello")
  assert result.content == "cached"


@pytest.mark.asyncio
async def test_openai_provider_delegates(monkeypatch) -> None:
  class Client:
    async def generate(self, **_kwargs):
      return {
        "content": "ok",
        "model": "gpt",
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2,
      }

    async def stream(self, **_kwargs):
      yield "a"

  provider = OpenAIProvider(client=Client())
  result = await provider.generate("hello")
  assert result.content == "ok"
  chunks = []
  async for chunk in provider.stream("hello"):
    chunks.append(chunk)
  assert chunks == ["a"]
