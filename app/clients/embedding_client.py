from abc import ABC, abstractmethod

from app.clients.gemini_client import GeminiClient
from app.clients.openai_client import OpenAIClient
from app.core.config import settings
from app.core.exceptions import AppException


class EmbeddingClient(ABC):
    """Abstract embedding client."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Create embeddings for a list of texts."""


class OpenAIEmbeddingClient(EmbeddingClient):
    """OpenAI embedding implementation."""

    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.OPENAI_API_KEY.strip():
            raise AppException(
                "OPENAI_API_KEY is required for embeddings. Set it in .env or switch EMBEDDING_PROVIDER=gemini.",
                status_code=400,
            )
        return await self._client.embed(texts, model=settings.EMBEDDING_MODEL)


class GeminiEmbeddingClient(EmbeddingClient):
    """Gemini embedding implementation."""

    def __init__(self, client: GeminiClient) -> None:
        self._client = client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.GEMINI_API_KEY.strip():
            raise AppException(
                "GEMINI_API_KEY is required for embeddings. Set it in .env.",
                status_code=400,
            )
        return await self._client.embed(texts, model=settings.EMBEDDING_MODEL)


def create_embedding_client(
    openai_client: OpenAIClient,
    gemini_client: GeminiClient,
) -> EmbeddingClient:
    """Create an embedding client based on EMBEDDING_PROVIDER or LLM_PROVIDER."""
    provider = (settings.EMBEDDING_PROVIDER or settings.LLM_PROVIDER).lower()
    if provider == "gemini":
        return GeminiEmbeddingClient(client=gemini_client)
    if provider == "openai":
        return OpenAIEmbeddingClient(client=openai_client)
    raise AppException(
        f"Unsupported embedding provider: {provider}. Use 'openai' or 'gemini'.",
        status_code=400,
    )
