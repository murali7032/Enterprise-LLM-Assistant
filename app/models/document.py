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


class DocumentSearchResponse(BaseModel):
    """Response from a document search."""

    query: str
    collection: str
    results: list[DocumentChunk] = Field(default_factory=list)
    total: int = 0


class DocumentDeleteResponse(BaseModel):
    """Response from a document delete."""

    document_id: str
    collection: str
    chunks_deleted: int
    message: str
