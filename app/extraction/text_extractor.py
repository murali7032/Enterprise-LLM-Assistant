from app.extraction.base import DocumentExtractor, ExtractedContent


class PlainTextExtractor(DocumentExtractor):
    """Extract text from plain text and markdown files."""

    source_type = "text"
    extensions = frozenset({"txt", "md", "markdown", "csv", "log"})

    async def extract_bytes(self, file_bytes: bytes, filename: str) -> ExtractedContent:
        text = file_bytes.decode("utf-8", errors="replace").strip()
        return ExtractedContent(
            text=text,
            source_type=self.source_type,
            filename=filename,
            metadata={"encoding": "utf-8"},
        )
