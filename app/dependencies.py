from fastapi import HTTPException

from app.core.config import settings

# ----------------------------
# Clients
# ----------------------------
from app.clients.openai_client import OpenAIClient
from app.clients.gemini_client import GeminiClient

# ----------------------------
# Providers
# ----------------------------
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.llm_provider import LLMProvider

# ----------------------------
# Services
# ----------------------------
from app.services.llm_service import LLMService
from app.services.chat_service import ChatService


# ==========================================================
# Client Factories
# ==========================================================

def get_openai_client() -> OpenAIClient:
    return OpenAIClient()


def get_gemini_client() -> GeminiClient:
    return GeminiClient()


# ==========================================================
# Provider Factories
# ==========================================================

def create_openai_provider() -> LLMProvider:
    return OpenAIProvider(
        client=get_openai_client()
    )


def create_gemini_provider() -> LLMProvider:
    return GeminiProvider(
        client=get_gemini_client()
    )


# ==========================================================
# Provider Registry
# ==========================================================

PROVIDER_REGISTRY = {
    "openai": create_openai_provider,
    "gemini": create_gemini_provider,
}


# ==========================================================
# Dependency Injection
# ==========================================================

def get_llm_provider() -> LLMProvider:

    provider_name = settings.LLM_PROVIDER.lower()

    factory = PROVIDER_REGISTRY.get(provider_name)

    if factory is None:
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported LLM Provider: {provider_name}"
        )

    return factory()


def get_llm_service() -> LLMService:

    return LLMService(
        provider=get_llm_provider()
    )


def get_chat_service() -> ChatService:

    return ChatService(
        llm_service=get_llm_service()
    )