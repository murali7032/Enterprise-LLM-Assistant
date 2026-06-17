from app.providers.openai_provider import (
    OpenAIProvider
)

from app.services.llm_service import (
    LLMService
)

from app.services.chat_service import (
    ChatService
)


def get_chat_service():

    provider = OpenAIProvider()

    llm_service = LLMService(
        provider
    )

    return ChatService(
        llm_service
    )