import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import UnsupportedExtractionException
# from app.extraction.pdf_extractor import PdfExtractor
from app.extraction.registry import ExtractionRegistry, get_default_extraction_registry
from app.extraction.text_extractor import PlainTextExtractor
from app.services.ingestion_service import IngestionService, RecursiveTextSplitter


def test_extraction_registry_resolves_pdf() -> None:
    registry = get_default_extraction_registry()
    extractor = registry.resolve_filename("report.pdf")
    assert extractor.source_type == "pdf"


def test_extraction_registry_unknown_extension() -> None:
    registry = get_default_extraction_registry()
    with pytest.raises(UnsupportedExtractionException):
        registry.resolve_filename("archive.zip")


@pytest.mark.asyncio
async def test_plain_text_extractor() -> None:
    extractor = PlainTextExtractor()
    result = await extractor.extract_bytes(b"hello world", "notes.txt")
    assert result.text == "hello world"
    assert result.source_type == "text"


@pytest.mark.asyncio
async def test_ingestion_service_uses_extraction_layer() -> None:
    registry = ExtractionRegistry(extractors=[PlainTextExtractor()])
    embedding_client = MagicMock()
    embedding_client.embed = AsyncMock(return_value=[[0.1], [0.2]])
    qdrant_client = MagicMock()
    qdrant_client.ensure_collection = AsyncMock()
    qdrant_client.upsert = AsyncMock()
    document_repository = MagicMock()
    document_repository.save_document = AsyncMock()

    service = IngestionService(
        embedding_client=embedding_client,
        qdrant_client=qdrant_client,
        document_repository=document_repository,
        extraction_registry=registry,
        splitter=RecursiveTextSplitter(chunk_size=5, chunk_overlap=0),
    )
    result = await service.ingest(
        file_bytes=b"abcdefghij",
        filename="sample.txt",
        collection="documents",
    )
    assert result["chunks_indexed"] >= 2
    assert result["source_type"] == "text"
    document_repository.save_document.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingestion_stores_session_id_in_metadata() -> None:
    registry = ExtractionRegistry(extractors=[PlainTextExtractor()])
    embedding_client = MagicMock()
    embedding_client.embed = AsyncMock(return_value=[[0.1]])
    qdrant_client = MagicMock()
    qdrant_client.ensure_collection = AsyncMock()
    qdrant_client.upsert = AsyncMock()
    document_repository = MagicMock()
    document_repository.save_document = AsyncMock()

    service = IngestionService(
        embedding_client=embedding_client,
        qdrant_client=qdrant_client,
        document_repository=document_repository,
        extraction_registry=registry,
        splitter=RecursiveTextSplitter(chunk_size=100, chunk_overlap=0),
    )
    await service.ingest(
        file_bytes=b"session scoped content",
        filename="notes.txt",
        collection="documents",
        metadata={"session_id": "chat-session-1"},
    )
    saved_metadata = document_repository.save_document.await_args.kwargs["metadata"]
    assert saved_metadata["session_id"] == "chat-session-1"
    upsert_payload = qdrant_client.upsert.await_args.kwargs["payloads"][0]
    assert upsert_payload["session_id"] == "chat-session-1"


@pytest.mark.asyncio
async def test_youtube_stub_raises() -> None:
    registry = get_default_extraction_registry()
    extractor = registry.resolve_url("https://www.youtube.com/watch?v=abc123")
    with pytest.raises(UnsupportedExtractionException):
        await extractor.extract_url("https://www.youtube.com/watch?v=abc123")
