from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings


class OpenAIClient:
    """Thin wrapper around the OpenAI SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Create a chat completion."""
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
        """Stream a chat completion."""
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

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Create embeddings for a list of texts."""
        response = await self._client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]
