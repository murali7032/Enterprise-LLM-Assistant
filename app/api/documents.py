from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_document_service, get_ingestion_service
from app.middleware.auth import require_auth_permission
from app.models.document import (
    DocumentDeleteResponse,
    DocumentIngestRequest,
    DocumentSearchRequest,
    DocumentSearchResponse,
)
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/ingest")
async def ingest_document(
    collection: str = "documents",
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    _user: dict = Depends(require_auth_permission("documents")),
) -> dict:
    """Ingest a PDF document into the vector store."""
    content = await file.read()
    request = DocumentIngestRequest(collection=collection)
    return await ingestion_service.ingest_pdf(
        file_bytes=content,
        filename=file.filename or "upload.pdf",
        collection=request.collection,
        metadata=request.metadata,
    )


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
