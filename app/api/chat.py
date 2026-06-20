import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service, get_document_service, get_ingestion_service
from app.middleware.auth import require_auth_permission
from app.models.chat_request import ChatRequest, ChatUploadUrlRequest
from app.models.chat_response import ChatResponse
from app.models.document import DocumentIngestResponse, SessionDocumentsDeleteResponse
from app.services.chat_document_metadata import build_chat_document_metadata
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> ChatResponse:
    """Generate a chat response."""
    return await chat_service.chat(request)


@router.post("/chat/upload", response_model=DocumentIngestResponse)
async def chat_upload(
    session_id: str,
    file: UploadFile = File(...),
    collection: str = "documents",
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> DocumentIngestResponse:
    """Upload a document from chat and index it for session-scoped RAG."""
    content = await file.read()
    filename = file.filename or "upload.bin"
    result = await ingestion_service.ingest(
        file_bytes=content,
        filename=filename,
        collection=collection,
        metadata=build_chat_document_metadata(session_id),
    )
    return DocumentIngestResponse(**result)


@router.delete("/chat/session/{session_id}/documents", response_model=SessionDocumentsDeleteResponse)
async def delete_chat_session_documents(
    session_id: str,
    collection: str = "documents",
    document_service: DocumentService = Depends(get_document_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> SessionDocumentsDeleteResponse:
    """Delete ephemeral documents uploaded for a chat session."""
    result = await document_service.delete_session_documents(
        session_id=session_id,
        collection=collection,
        ephemeral_only=True,
    )
    return SessionDocumentsDeleteResponse(**result)


@router.post("/chat/upload-url", response_model=DocumentIngestResponse)
async def chat_upload_url(
    request: ChatUploadUrlRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> DocumentIngestResponse:
    """Ingest a URL from chat and index it for session-scoped RAG."""
    metadata = build_chat_document_metadata(request.session_id, request.metadata)
    result = await ingestion_service.ingest_url(
        url=request.url,
        collection=request.collection,
        metadata=metadata,
    )
    return DocumentIngestResponse(**result)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> StreamingResponse:
    """Stream a chat response using Server-Sent Events."""

    async def event_generator() -> AsyncIterator[str]:
        async for event in chat_service.stream_events(request):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
