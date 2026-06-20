import pytest
from unittest.mock import AsyncMock, MagicMock

from app.repositories.in_memory_document_repository import InMemoryDocumentRepository
from app.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_delete_session_documents_ephemeral_only() -> None:
    repo = InMemoryDocumentRepository()
    await repo.save_document(
        "doc-1",
        "chat.pdf",
        "documents",
        2,
        {"session_id": "s1", "ephemeral": True},
    )
    await repo.save_document(
        "doc-2",
        "permanent.pdf",
        "documents",
        1,
        {"session_id": "s1"},
    )

    qdrant_client = MagicMock()
    qdrant_client.delete_by_session_id = AsyncMock(return_value=4)
    service = DocumentService(
        embedding_client=MagicMock(),
        retriever=MagicMock(),
        qdrant_client=qdrant_client,
        document_repository=repo,
    )

    result = await service.delete_session_documents("s1", "documents", ephemeral_only=True)

    assert result["documents_deleted"] == 1
    assert result["document_ids"] == ["doc-1"]
    assert result["chunks_deleted"] == 4
    assert await repo.get_document("doc-1") is None
    assert await repo.get_document("doc-2") is not None
