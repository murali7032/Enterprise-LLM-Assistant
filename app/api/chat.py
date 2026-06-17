from fastapi import APIRouter, Depends

from app.dependencies import get_chat_service
from app.models.chat_request import ChatRequest
from app.models.chat_response import ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(
    prefix="/api/v1",
    tags=["Chat"]
)


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):

    answer = chat_service.chat(request.question)

    return ChatResponse(answer=answer)