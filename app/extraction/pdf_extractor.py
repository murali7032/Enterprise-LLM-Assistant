from io import BytesIO

from pypdf import PdfReader

from app.extraction.base import DocumentExtractor, ExtractedContent


class PdfExtractor(DocumentExtractor):
    """Extract text from PDF documents."""

    source_type = "pdf"
    extensions = frozenset({"pdf"})

    async def extract_bytes(self, file_bytes: bytes, filename: str) -> ExtractedContent:
        reader = PdfReader(BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return ExtractedContent(
            text=text.strip(),
            source_type=self.source_type,
            filename=filename,
            metadata={"page_count": len(reader.pages)},
        )
