from collections.abc import AsyncIterator
from typing import Any

import google.generativeai as genai

from app.core.config import settings


class GeminiClient:
    """Thin wrapper around the Google Generative AI SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        genai.configure(api_key=api_key or settings.GEMINI_API_KEY)
        self._api_key = api_key or settings.GEMINI_API_KEY

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Generate content from Gemini."""
        client = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        response = await client.generate_content_async(prompt)
        usage = getattr(response, "usage_metadata", None)
        return {
            "content": response.text or "",
            "model": model,
            "prompt_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "completion_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
            "total_tokens": getattr(usage, "total_token_count", 0) if usage else 0,
        }

    async def stream(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream content from Gemini."""
        client = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        response = await client.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Create embeddings for a list of texts."""
        import asyncio

        async def _embed_one(text: str) -> list[float]:
            result = await asyncio.to_thread(
                genai.embed_content,
                model=model,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]

        return await asyncio.gather(*[_embed_one(text) for text in texts])
