from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request payload."""

    question: str = Field(..., min_length=1)
    session_id: str | None = None
    use_rag: bool = False
    use_memory: bool = True
    collection: str = "documents"
    metadata_filter: dict[str, Any] = Field(default_factory=dict)
