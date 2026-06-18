from collections.abc import AsyncIterator

from app.clients.openai_client import OpenAIClient
from app.core.config import settings
from app.models.llm_response import LLMResult
from app.providers.llm_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, client: OpenAIClient | None = None) -> None:
        self._client = client or OpenAIClient()

    @property
    def name(self) -> str:
        return "openai"

    async def generate(self, prompt: str) -> LLMResult:
        response = await self._client.generate(
            prompt=prompt,
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )
        return LLMResult(
            content=response["content"],
            model=response["model"],
            prompt_tokens=response["prompt_tokens"],
            completion_tokens=response["completion_tokens"],
            total_tokens=response["total_tokens"],
        )

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        async for chunk in self._client.stream(
            prompt=prompt,
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        ):
            yield chunk


def create_openai_provider(client: OpenAIClient) -> LLMProvider:
    """Factory for OpenAI provider."""
    return OpenAIProvider(client=client)
