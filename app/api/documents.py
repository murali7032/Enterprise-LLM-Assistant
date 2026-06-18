from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_ingestion_service
from app.middleware.auth import require_auth_permission
from app.models.document import DocumentIngestRequest, DocumentSearchRequest
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


@router.post("/search")
async def search_documents(
    request: DocumentSearchRequest,
    _user: dict = Depends(require_auth_permission("documents")),
) -> dict:
    """Document search endpoint placeholder for repository-backed search."""
    return {
        "query": request.query,
        "collection": request.collection,
        "top_k": request.top_k,
        "message": "Use chat with use_rag=true for retrieval-augmented answers.",
    }
