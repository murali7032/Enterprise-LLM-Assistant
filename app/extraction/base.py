from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedContent:
    """Normalized text output from any document/media extractor."""

    text: str
    source_type: str
    filename: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentExtractor(ABC):
    """Extract plain text from a file or URL."""

    source_type: str = "unknown"
    extensions: frozenset[str] = frozenset()
    url_patterns: tuple[str, ...] = ()

    @abstractmethod
    async def extract_bytes(self, file_bytes: bytes, filename: str) -> ExtractedContent:
        """Extract text from raw file bytes."""

    async def extract_url(self, url: str) -> ExtractedContent:
        """Extract text from a remote URL (optional per extractor)."""
        raise NotImplementedError(f"{self.source_type} URL extraction is not implemented")

    def supports_filename(self, filename: str) -> bool:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return extension in self.extensions

    def supports_url(self, url: str) -> bool:
        lowered = url.lower()
        return any(pattern in lowered for pattern in self.url_patterns)
