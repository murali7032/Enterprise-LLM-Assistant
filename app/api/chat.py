import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service
from app.middleware.auth import require_auth_permission
from app.models.chat_request import ChatRequest
from app.models.chat_response import ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> ChatResponse:
    """Generate a chat response."""
    return await chat_service.chat(request)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    _user: dict = Depends(require_auth_permission("chat")),
) -> StreamingResponse:
    """Stream a chat response using Server-Sent Events."""

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in chat_service.stream(request):
            payload = json.dumps({"content": chunk})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
