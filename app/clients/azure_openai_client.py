from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncAzureOpenAI

from app.core.config import settings


class AzureOpenAIClient:
    """Thin wrapper around the Azure OpenAI SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=api_key or settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=endpoint or settings.AZURE_OPENAI_ENDPOINT,
            api_version=api_version or settings.AZURE_OPENAI_API_VERSION,
        )

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Create an Azure chat completion."""
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = response.usage
        return {
            "content": response.choices[0].message.content or "",
            "model": response.model,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }

    async def stream(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream an Azure chat completion."""
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
