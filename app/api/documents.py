from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_document_service, get_ingestion_service
from app.middleware.auth import require_auth_permission
from app.models.document import (
    DocumentDeleteResponse,
    DocumentIngestResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUrlIngestRequest,
)
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.get("/supported-types")
async def list_supported_types(
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    _user: dict = Depends(require_auth_permission("documents")),
) -> dict[str, list[str]]:
    """List registered file extensions and source types for ingestion."""
    return {
        "extensions": ingestion_service.supported_extensions(),
        "source_types": ingestion_service.supported_source_types(),
    }


@router.post("/ingest", response_model=DocumentIngestResponse)
async def ingest_document(
    collection: str = "documents",
    session_id: str | None = None,
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    _user: dict = Depends(require_auth_permission("documents")),
) -> DocumentIngestResponse:
    """Ingest a document file into the vector store."""
    content = await file.read()
    filename = file.filename or "upload.bin"
    metadata: dict = {}
    if session_id:
        metadata["session_id"] = session_id
    result = await ingestion_service.ingest(
        file_bytes=content,
        filename=filename,
        collection=collection,
        metadata=metadata,
    )
    return DocumentIngestResponse(**result)


@router.post("/ingest-url", response_model=DocumentIngestResponse)
async def ingest_document_url(
    request: DocumentUrlIngestRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    _user: dict = Depends(require_auth_permission("documents")),
) -> DocumentIngestResponse:
    """Ingest content from a URL (YouTube and others when enabled)."""
    metadata = dict(request.metadata)
    if request.session_id:
        metadata["session_id"] = request.session_id
    result = await ingestion_service.ingest_url(
        url=request.url,
        collection=request.collection,
        metadata=metadata,
    )
    return DocumentIngestResponse(**result)


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    document_service: DocumentService = Depends(get_document_service),
    _user: dict = Depends(require_auth_permission("documents")),
) -> DocumentSearchResponse:
    """Search document chunks in the vector store."""
    return await document_service.search(request)


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    collection: str = "documents",
    document_service: DocumentService = Depends(get_document_service),
    _user: dict = Depends(require_auth_permission("documents")),
) -> DocumentDeleteResponse:
    """Delete a document and all its vector chunks from the collection."""
    return await document_service.delete(document_id=document_id, collection=collection)
