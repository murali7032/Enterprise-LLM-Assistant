from functools import lru_cache

from app.core.exceptions import UnsupportedExtractionException
from app.extraction.base import DocumentExtractor
from app.extraction.pdf_extractor import PdfExtractor
from app.extraction.stub_extractors import (
    AudioExtractor,
    ExcelExtractor,
    PowerPointExtractor,
    VideoExtractor,
    YoutubeExtractor,
)
from app.extraction.text_extractor import PlainTextExtractor


class ExtractionRegistry:
    """Resolve extractors by filename extension or URL pattern."""

    def __init__(self, extractors: list[DocumentExtractor] | None = None) -> None:
        self._extractors = extractors or []
        self._by_extension: dict[str, DocumentExtractor] = {}
        self._url_extractors: list[DocumentExtractor] = []
        for extractor in self._extractors:
            for extension in extractor.extensions:
                self._by_extension[extension.lower()] = extractor
            if extractor.url_patterns:
                self._url_extractors.append(extractor)

    def register(self, extractor: DocumentExtractor) -> None:
        """Register an extractor at runtime."""
        for extension in extractor.extensions:
            self._by_extension[extension.lower()] = extractor
        if extractor.url_patterns:
            self._url_extractors.append(extractor)

    def list_supported_extensions(self) -> list[str]:
        """Return all registered file extensions."""
        return sorted(self._by_extension.keys())

    def list_source_types(self) -> list[str]:
        """Return unique source types."""
        return sorted({extractor.source_type for extractor in self._extractors})

    def resolve_filename(self, filename: str) -> DocumentExtractor:
        """Find an extractor for a filename."""
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        extractor = self._by_extension.get(extension)
        if extractor is None:
            supported = ", ".join(self.list_supported_extensions()) or "none"
            raise UnsupportedExtractionException(
                f"Unsupported file type '.{extension}'. Supported extensions: {supported}"
            )
        return extractor

    def resolve_url(self, url: str) -> DocumentExtractor:
        """Find an extractor for a URL."""
        for extractor in self._url_extractors:
            if extractor.supports_url(url):
                return extractor
        raise UnsupportedExtractionException(
            "Unsupported URL. Currently only YouTube links are reserved for future extraction."
        )


@lru_cache
def get_default_extraction_registry() -> ExtractionRegistry:
    """Build the default registry with all built-in extractors."""
    return ExtractionRegistry(
        extractors=[
            PdfExtractor(),
            PlainTextExtractor(),
            ExcelExtractor(),
            PowerPointExtractor(),
            AudioExtractor(),
            VideoExtractor(),
            YoutubeExtractor(),
        ]
    )
