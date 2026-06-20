import pytest

from app.memory.conversation_memory import InMemoryConversationMemory
from app.repositories.in_memory_document_repository import InMemoryDocumentRepository
from app.retrieval.retriever import HybridSearch, Reranker
from app.services.ingestion_service import RecursiveTextSplitter
from app.tools.shell_tool import ShellTool
from app.tools.sql_tool import SQLTool


def test_recursive_splitter() -> None:
  splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=2)
  chunks = splitter.split("abcdefghijklmnop")
  assert len(chunks) >= 2


@pytest.mark.asyncio
async def test_document_repository() -> None:
  repo = InMemoryDocumentRepository()
  await repo.save_document("1", "file.pdf", "documents", 3, {"tag": "a"})
  doc = await repo.get_document("1")
  assert doc is not None
  docs = await repo.list_documents("documents")
  assert len(docs) == 1


def test_hybrid_search_ranking() -> None:
  search = HybridSearch()
  ranked = search.rank(
    "kubernetes deployment",
    [
      {"id": "1", "score": 0.5, "payload": {"content": "kubernetes deployment guide"}},
      {"id": "2", "score": 0.9, "payload": {"content": "unrelated"}},
    ],
  )
  assert ranked[0]["id"] == "1"


def test_reranker() -> None:
  reranker = Reranker(HybridSearch())
  chunks = reranker.rerank(
    "kubernetes",
    [{"id": "1", "score": 0.8, "payload": {"content": "kubernetes pods"}}],
  )
  assert chunks[0].content == "kubernetes pods"


@pytest.mark.asyncio
async def test_shell_tool_allowed() -> None:
  tool = ShellTool()
  result = await tool.execute("pwd")
  assert result["exit_code"] == 0


@pytest.mark.asyncio
async def test_sql_tool() -> None:
  tool = SQLTool()
  result = await tool.execute("select 1")
  assert result["row_count"] == 1


@pytest.mark.asyncio
async def test_conversation_memory() -> None:
  memory = InMemoryConversationMemory()
  await memory.append("s1", "user", "hello")
  await memory.append("s1", "assistant", "hi")
  assert len(await memory.get_history("s1")) == 2
