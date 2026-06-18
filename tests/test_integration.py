from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_qdrant_client, get_redis_client
from app.main import app
from app.models.chat_request import ChatRequest
from app.models.document import DocumentChunk
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.security.guardrails import PromptGuardrails
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService
from app.tools.kubernetes_tool import KubernetesTool
from tests.conftest import FakeProvider


@pytest.mark.asyncio
async def test_chat_service_rag_path() -> None:
  retriever = MagicMock()
  retriever.retrieve = AsyncMock(
    return_value=[DocumentChunk(id="1", content="k8s docs", score=0.9, metadata={})]
  )
  openai_client = MagicMock()
  openai_client.embed = AsyncMock(return_value=[[0.1, 0.2]])
  service = ChatService(
    llm_service=LLMService(provider=FakeProvider(), cache=None),
    prompt_builder=PromptBuilder(),
    output_parser=OutputParser(),
    guardrails=PromptGuardrails(),
    retriever=retriever,
    openai_client=openai_client,
  )
  response = await service.chat(ChatRequest(question="search kubernetes docs", use_rag=True))
  assert response.sources
  assert response.answer.startswith("answer:")


@pytest.mark.asyncio
async def test_kubernetes_tool() -> None:
  tool = KubernetesTool()
  result = await tool.execute("pods")
  assert result["status"] == "Running"


def test_health_ready_with_mocks() -> None:
  redis = MagicMock()
  redis.ping = AsyncMock(return_value=True)
  qdrant = MagicMock()
  qdrant.health = AsyncMock(return_value=True)
  app.dependency_overrides[get_redis_client] = lambda: redis
  app.dependency_overrides[get_qdrant_client] = lambda: qdrant
  with TestClient(app) as client:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "READY"
  app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_service_stream() -> None:
  service = ChatService(
    llm_service=LLMService(provider=FakeProvider(), cache=None),
    prompt_builder=PromptBuilder(),
    output_parser=OutputParser(),
    guardrails=PromptGuardrails(),
  )
  chunks = []
  async for chunk in service.stream(ChatRequest(question="hello")):
    chunks.append(chunk)
  assert chunks == ["chunk"]
