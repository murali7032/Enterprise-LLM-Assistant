from typing import Any

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Chat response payload."""

    answer: str
    session_id: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    cached: bool = False
