from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import settings


class AnthropicClient:
    """Thin wrapper around the Anthropic SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self._client = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Create a message completion."""
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text
        usage = response.usage
        return {
            "content": content,
            "model": response.model,
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
            "total_tokens": usage.input_tokens + usage.output_tokens,
        }

    async def stream(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream a message completion."""
        async with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
