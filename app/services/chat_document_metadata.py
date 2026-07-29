from typing import Any

from app.core.config import settings


def build_chat_document_metadata(
    session_id: str, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build metadata for documents uploaded from chat."""
    metadata: dict[str, Any] = {"session_id": session_id}
    if settings.EPHEMERAL_CHAT_DOCUMENTS:
        metadata["ephemeral"] = True
    if extra:
        metadata.update(extra)
    return metadata
