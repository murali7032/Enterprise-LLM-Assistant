from typing import Any
from uuid import uuid4

from app.clients.embedding_client import EmbeddingClient
from app.clients.qdrant_client import QdrantClientWrapper
from app.core.config import settings
from app.core.exceptions import AppException
from app.extraction.registry import ExtractionRegistry, get_default_extraction_registry
from app.repositories.document_repository import DocumentRepository


class RecursiveTextSplitter:
    """Split text recursively using configurable chunk size and overlap."""

    def __init__(
        self, chunk_size: int | None = None, chunk_overlap: int | None = None
    ) -> None:
        self._chunk_size = chunk_size or settings.CHUNK_SIZE
        self._chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def split(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        chunks: list[str] = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + self._chunk_size, text_length)
            chunks.append(text[start:end])
            if end == text_length:
                break
            start = max(end - self._chunk_overlap, start + 1)
        return chunks


class IngestionService:
    """Orchestrate extraction, chunking, embedding, and vector indexing."""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        qdrant_client: QdrantClientWrapper,
        document_repository: DocumentRepository,
        extraction_registry: ExtractionRegistry | None = None,
        splitter: RecursiveTextSplitter | None = None,
    ) -> None:
        self._embedding_client = embedding_client
        self._qdrant_client = qdrant_client
        self._document_repository = document_repository
        self._extraction_registry = (
            extraction_registry or get_default_extraction_registry()
        )
        self._splitter = splitter or RecursiveTextSplitter()

    async def ingest(
        self,
        file_bytes: bytes,
        filename: str,
        collection: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract text from a file, chunk, embed, and store in the vector database."""
        extractor = self._extraction_registry.resolve_filename(filename)
        extracted = await extractor.extract_bytes(file_bytes, filename)
        return await self._index_text(
            text=extracted.text,
            filename=filename,
            collection=collection,
            metadata={
                **(metadata or {}),
                "source_type": extracted.source_type,
                **extracted.metadata,
            },
        )

    async def ingest_url(
        self,
        url: str,
        collection: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract text from a URL, chunk, embed, and store in the vector database."""
        extractor = self._extraction_registry.resolve_url(url)
        extracted = await extractor.extract_url(url)
        filename = extracted.filename or url
        return await self._index_text(
            text=extracted.text,
            filename=filename,
            collection=collection,
            metadata={
                **(metadata or {}),
                "source_type": extracted.source_type,
                "source_url": url,
                **extracted.metadata,
            },
        )

    async def ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        collection: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible PDF ingest entrypoint."""
        return await self.ingest(file_bytes, filename, collection, metadata)

    def supported_extensions(self) -> list[str]:
        """Return file extensions registered for ingestion."""
        return self._extraction_registry.list_supported_extensions()

    def supported_source_types(self) -> list[str]:
        """Return registered extractor source types."""
        return self._extraction_registry.list_source_types()

    async def _index_text(
        self,
        text: str,
        filename: str,
        collection: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        chunks = self._splitter.split(text)
        if not chunks:
            raise AppException("No extractable text found in document", status_code=422)

        embeddings = await self._embedding_client.embed(chunks)
        await self._qdrant_client.ensure_collection(
            collection, settings.EMBEDDING_DIMENSION
        )

        document_id = str(uuid4())
        payloads = [
            {
                "content": chunk,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
                **metadata,
            }
            for index, chunk in enumerate(chunks)
        ]
        await self._qdrant_client.upsert(
            collection=collection, vectors=embeddings, payloads=payloads
        )
        await self._document_repository.save_document(
            document_id=document_id,
            filename=filename,
            collection=collection,
            chunk_count=len(chunks),
            metadata=metadata,
        )
        return {
            "document_id": document_id,
            "filename": filename,
            "chunks_indexed": len(chunks),
            "source_type": metadata.get("source_type", "unknown"),
            "collection": collection,
        }
