from io import BytesIO
from typing import Any
from uuid import uuid4

from pypdf import PdfReader

from app.clients.openai_client import OpenAIClient
from app.clients.qdrant_client import QdrantClientWrapper
from app.core.config import settings
from app.repositories.document_repository import DocumentRepository


class RecursiveTextSplitter:
    """Split text recursively using configurable chunk size and overlap."""

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
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
    """Ingest PDF documents into the vector store."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        qdrant_client: QdrantClientWrapper,
        document_repository: DocumentRepository,
        splitter: RecursiveTextSplitter | None = None,
    ) -> None:
        self._openai_client = openai_client
        self._qdrant_client = qdrant_client
        self._document_repository = document_repository
        self._splitter = splitter or RecursiveTextSplitter()

    async def ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        collection: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Parse, chunk, embed, and store a PDF document."""
        reader = PdfReader(BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        chunks = self._splitter.split(text)
        if not chunks:
            return {"document_id": None, "chunks_indexed": 0}

        embeddings = await self._openai_client.embed(chunks, model=settings.EMBEDDING_MODEL)
        await self._qdrant_client.ensure_collection(collection, settings.EMBEDDING_DIMENSION)

        document_id = str(uuid4())
        payloads = [
            {
                "content": chunk,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
                **(metadata or {}),
            }
            for index, chunk in enumerate(chunks)
        ]
        await self._qdrant_client.upsert(collection=collection, vectors=embeddings, payloads=payloads)
        await self._document_repository.save_document(
            document_id=document_id,
            filename=filename,
            collection=collection,
            chunk_count=len(chunks),
            metadata=metadata or {},
        )
        return {"document_id": document_id, "chunks_indexed": len(chunks)}
