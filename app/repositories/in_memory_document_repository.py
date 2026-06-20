from typing import Any

from app.repositories.document_repository import DocumentRepository


class InMemoryDocumentRepository(DocumentRepository):
    """In-memory document metadata repository."""

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}

    async def save_document(
        self,
        document_id: str,
        filename: str,
        collection: str,
        chunk_count: int,
        metadata: dict[str, Any],
    ) -> None:
        self._documents[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "collection": collection,
            "chunk_count": chunk_count,
            "metadata": metadata,
        }

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        return self._documents.get(document_id)

    async def list_documents(self, collection: str | None = None) -> list[dict[str, Any]]:
        documents = list(self._documents.values())
        if collection:
            return [doc for doc in documents if doc["collection"] == collection]
        return documents

    async def delete_document(self, document_id: str) -> bool:
        return self._documents.pop(document_id, None) is not None

    async def list_documents_by_session(
        self,
        session_id: str,
        collection: str | None = None,
        ephemeral_only: bool = False,
    ) -> list[dict[str, Any]]:
        documents = [
            doc
            for doc in self._documents.values()
            if doc.get("metadata", {}).get("session_id") == session_id
            and (not ephemeral_only or doc.get("metadata", {}).get("ephemeral") is True)
        ]
        if collection:
            return [doc for doc in documents if doc["collection"] == collection]
        return documents

    async def delete_documents_by_session(
        self,
        session_id: str,
        ephemeral_only: bool = True,
    ) -> list[str]:
        to_delete = await self.list_documents_by_session(session_id, ephemeral_only=ephemeral_only)
        deleted_ids: list[str] = []
        for doc in to_delete:
            if await self.delete_document(doc["document_id"]):
                deleted_ids.append(doc["document_id"])
        return deleted_ids
