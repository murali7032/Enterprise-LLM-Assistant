import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_chat_service, get_llm_provider, get_llm_service
from app.main import app
from app.models.llm_response import LLMResult
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.providers.llm_provider import LLMProvider
from app.security.guardrails import PromptGuardrails
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService


class FakeProvider(LLMProvider):
  @property
  def name(self) -> str:
    return "fake"

  async def generate(self, prompt: str) -> LLMResult:
    return LLMResult(content=f"answer: {prompt}", model="fake", prompt_tokens=1, completion_tokens=2, total_tokens=3)

  async def stream(self, prompt: str):
    yield "chunk"


@pytest.fixture
def client() -> TestClient:
  fake_provider = FakeProvider()
  llm_service = LLMService(provider=fake_provider, cache=None)
  chat_service = ChatService(
    llm_service=llm_service,
    prompt_builder=PromptBuilder(),
    output_parser=OutputParser(),
    guardrails=PromptGuardrails(),
    retriever=None,
    openai_client=None,
  )
  app.dependency_overrides[get_llm_provider] = lambda: fake_provider
  app.dependency_overrides[get_llm_service] = lambda: llm_service
  app.dependency_overrides[get_chat_service] = lambda: chat_service
  with TestClient(app) as test_client:
    yield test_client
  app.dependency_overrides.clear()
