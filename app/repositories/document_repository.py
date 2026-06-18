from typing import Any


class DocumentRepository:
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
        """Persist document metadata."""
        self._documents[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "collection": collection,
            "chunk_count": chunk_count,
            "metadata": metadata,
        }

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        """Fetch document metadata by ID."""
        return self._documents.get(document_id)

    async def list_documents(self, collection: str | None = None) -> list[dict[str, Any]]:
        """List stored document metadata."""
        documents = list(self._documents.values())
        if collection:
            return [doc for doc in documents if doc["collection"] == collection]
        return documents
