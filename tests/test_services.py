import pytest

from app.cache.cache_key import build_cache_key
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.providers.registry import ProviderRegistry
from app.security.authentication import create_access_token, decode_access_token, require_permission
from app.services.llm_service import LLMService
from tests.conftest import FakeProvider


def test_cache_key_is_deterministic() -> None:
  key_a = build_cache_key("llm", {"prompt": "hello"})
  key_b = build_cache_key("llm", {"prompt": "hello"})
  assert key_a == key_b


def test_llm_service_generate_with_fake_provider() -> None:
  pass


@pytest.mark.asyncio
async def test_llm_service_generate_with_fake_provider_async() -> None:
  service = LLMService(provider=FakeProvider(), cache=None)
  result = await service.generate("hello")
  assert "hello" in result.content


def test_registry_unknown_provider() -> None:
  registry = ProviderRegistry()
  with pytest.raises(Exception):
    registry.create("missing")


def test_auth_token_roundtrip() -> None:
  token = create_access_token("user-1", "admin")
  payload = decode_access_token(token)
  assert payload["sub"] == "user-1"
  require_permission("admin", "chat")


def test_prompt_builder_agent_prompt() -> None:
  builder = PromptBuilder()
  prompt = builder.build_agent_prompt("deploy app", ["step 1"], ["weather"])
  assert "deploy app" in prompt


def test_output_parser_text() -> None:
  parser = OutputParser()
  assert parser.parse_text("  answer  ") == "answer"
