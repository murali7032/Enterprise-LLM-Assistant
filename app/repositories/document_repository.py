from abc import ABC, abstractmethod
from typing import Any


class DocumentRepository(ABC):
    """Document metadata persistence interface."""

    @abstractmethod
    async def save_document(
        self,
        document_id: str,
        filename: str,
        collection: str,
        chunk_count: int,
        metadata: dict[str, Any],
    ) -> None:
        """Persist document metadata."""

    @abstractmethod
    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        """Fetch document metadata by ID."""

    @abstractmethod
    async def list_documents(self, collection: str | None = None) -> list[dict[str, Any]]:
        """List stored document metadata."""

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Remove document metadata by ID."""

    @abstractmethod
    async def list_documents_by_session(
        self,
        session_id: str,
        collection: str | None = None,
        ephemeral_only: bool = False,
    ) -> list[dict[str, Any]]:
        """List document metadata for a chat session."""

    @abstractmethod
    async def delete_documents_by_session(
        self,
        session_id: str,
        ephemeral_only: bool = True,
    ) -> list[str]:
        """Delete document metadata for a session. Returns removed document IDs."""
