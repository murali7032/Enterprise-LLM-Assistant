from typing import Any

from app.clients.embedding_client import EmbeddingClient
from app.clients.qdrant_client import QdrantClientWrapper
from app.core.exceptions import AppException
from app.models.document import DocumentDeleteResponse, DocumentSearchRequest, DocumentSearchResponse
from app.repositories.document_repository import DocumentRepository
from app.retrieval.retriever import Retriever


class DocumentService:
    """Document search and management operations."""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        retriever: Retriever,
        qdrant_client: QdrantClientWrapper,
        document_repository: DocumentRepository,
    ) -> None:
        self._embedding_client = embedding_client
        self._retriever = retriever
        self._qdrant_client = qdrant_client
        self._document_repository = document_repository

    async def search(self, request: DocumentSearchRequest) -> DocumentSearchResponse:
        """Search document chunks in the vector store."""
        embeddings = await self._embedding_client.embed([request.query])
        chunks = await self._retriever.retrieve(
            query_vector=embeddings[0],
            query_text=request.query,
            collection=request.collection,
            top_k=request.top_k,
            top_n=request.top_k,
            metadata_filter=request.metadata_filter or None,
        )
        return DocumentSearchResponse(
            query=request.query,
            collection=request.collection,
            results=chunks,
            total=len(chunks),
        )

    async def delete(self, document_id: str, collection: str) -> DocumentDeleteResponse:
        """Delete a document and all its vector chunks."""
        chunks_deleted = await self._qdrant_client.delete_by_document_id(collection, document_id)
        if chunks_deleted == 0:
            raise AppException(
                message=f"Document '{document_id}' not found in collection '{collection}'",
                status_code=404,
            )

        await self._document_repository.delete_document(document_id)
        return DocumentDeleteResponse(
            document_id=document_id,
            collection=collection,
            chunks_deleted=chunks_deleted,
            message="Document deleted successfully",
        )

    async def delete_session_documents(
        self,
        session_id: str,
        collection: str,
        ephemeral_only: bool = True,
    ) -> dict[str, Any]:
        """Delete all documents (and vector chunks) for a chat session."""
        document_ids = await self._document_repository.delete_documents_by_session(
            session_id=session_id,
            ephemeral_only=ephemeral_only,
        )
        chunks_deleted = await self._qdrant_client.delete_by_session_id(collection, session_id)
        return {
            "session_id": session_id,
            "collection": collection,
            "documents_deleted": len(document_ids),
            "chunks_deleted": chunks_deleted,
            "document_ids": document_ids,
        }
