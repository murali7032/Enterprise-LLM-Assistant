from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_document_service
from app.main import app
from app.models.document import (
  DocumentChunk,
  DocumentDeleteResponse,
  DocumentSearchRequest,
  DocumentSearchResponse,
)
from app.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_document_service_search() -> None:
  embedding_client = MagicMock()
  embedding_client.embed = AsyncMock(return_value=[[0.1, 0.2]])
  retriever = MagicMock()
  retriever.retrieve = AsyncMock(
    return_value=[DocumentChunk(id="1", content="kubernetes guide", score=0.9, metadata={"filename": "k8s.pdf"})]
  )
  service = DocumentService(
    embedding_client=embedding_client,
    retriever=retriever,
    qdrant_client=MagicMock(),
    document_repository=MagicMock(),
  )
  response = await service.search(DocumentSearchRequest(query="kubernetes", collection="documents"))
  assert response.total == 1
  assert response.results[0].content == "kubernetes guide"


def test_search_endpoint_with_mock(client: TestClient) -> None:
  mock_service = MagicMock()
  mock_service.search = AsyncMock(
    return_value=DocumentSearchResponse(
      query="kubernetes",
      collection="documents",
      results=[DocumentChunk(id="1", content="kubernetes guide", score=0.9)],
      total=1,
    )
  )
  app.dependency_overrides[get_document_service] = lambda: mock_service
  token = client.post("/api/v1/auth/token").json()["access_token"]
  response = client.post(
    "/api/v1/documents/search",
    json={"query": "kubernetes", "collection": "documents", "top_k": 5},
    headers={"Authorization": f"Bearer {token}"},
  )
  app.dependency_overrides.pop(get_document_service, None)
  assert response.status_code == 200
  data = response.json()
  assert data["total"] == 1
  assert data["results"][0]["content"] == "kubernetes guide"


@pytest.mark.asyncio
async def test_document_service_delete() -> None:
  qdrant_client = MagicMock()
  qdrant_client.delete_by_document_id = AsyncMock(return_value=3)
  document_repository = MagicMock()
  document_repository.delete_document = AsyncMock(return_value=True)
  service = DocumentService(
    embedding_client=MagicMock(),
    retriever=MagicMock(),
    qdrant_client=qdrant_client,
    document_repository=document_repository,
  )
  response = await service.delete("doc-123", "documents")
  assert response.chunks_deleted == 3
  assert response.document_id == "doc-123"


@pytest.mark.asyncio
async def test_document_service_delete_not_found() -> None:
  qdrant_client = MagicMock()
  qdrant_client.delete_by_document_id = AsyncMock(return_value=0)
  service = DocumentService(
    embedding_client=MagicMock(),
    retriever=MagicMock(),
    qdrant_client=qdrant_client,
    document_repository=MagicMock(),
  )
  from app.core.exceptions import AppException

  with pytest.raises(AppException) as exc:
    await service.delete("missing-doc", "documents")
  assert exc.value.status_code == 404


def test_delete_endpoint_with_mock(client: TestClient) -> None:
  mock_service = MagicMock()
  mock_service.delete = AsyncMock(
    return_value=DocumentDeleteResponse(
      document_id="doc-123",
      collection="documents",
      chunks_deleted=5,
      message="Document deleted successfully",
    )
  )
  app.dependency_overrides[get_document_service] = lambda: mock_service
  token = client.post("/api/v1/auth/token").json()["access_token"]
  response = client.delete(
    "/api/v1/documents/doc-123?collection=documents",
    headers={"Authorization": f"Bearer {token}"},
  )
  app.dependency_overrides.pop(get_document_service, None)
  assert response.status_code == 200
  data = response.json()
  assert data["chunks_deleted"] == 5
