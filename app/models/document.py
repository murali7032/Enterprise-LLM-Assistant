from typing import Any

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """Request to ingest a document."""

    collection: str = Field(default="documents", min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSearchRequest(BaseModel):
    """Request to search documents."""

    query: str = Field(..., min_length=1)
    collection: str = Field(default="documents", min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A retrieved document chunk."""

    id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
