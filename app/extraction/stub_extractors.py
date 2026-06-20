from app.core.exceptions import UnsupportedExtractionException
from app.extraction.base import DocumentExtractor, ExtractedContent


class _StubExtractor(DocumentExtractor):
    """Base class for extractors registered but not yet implemented."""

    def __init__(self, source_type: str, extensions: frozenset[str], message: str) -> None:
        self.source_type = source_type
        self.extensions = extensions
        self._message = message
        self.url_patterns: tuple[str, ...] = ()

    async def extract_bytes(self, file_bytes: bytes, filename: str) -> ExtractedContent:
        raise UnsupportedExtractionException(self._message)


class ExcelExtractor(_StubExtractor):
    def __init__(self) -> None:
        super().__init__(
            "excel",
            frozenset({"xlsx", "xls", "xlsm"}),
            "Excel extraction is not enabled yet. Add openpyxl/xlrd and implement ExcelExtractor.",
        )


class PowerPointExtractor(_StubExtractor):
    def __init__(self) -> None:
        super().__init__(
            "powerpoint",
            frozenset({"ppt", "pptx"}),
            "PowerPoint extraction is not enabled yet. Add python-pptx and implement PowerPointExtractor.",
        )


class AudioExtractor(_StubExtractor):
    def __init__(self) -> None:
        super().__init__(
            "audio",
            frozenset({"mp3", "wav", "m4a", "ogg", "flac"}),
            "Audio transcription is not enabled yet. Add whisper/faster-whisper and implement AudioExtractor.",
        )


class VideoExtractor(_StubExtractor):
    def __init__(self) -> None:
        super().__init__(
            "video",
            frozenset({"mp4", "mov", "avi", "mkv", "webm"}),
            "Video extraction is not enabled yet. Add ffmpeg + speech-to-text pipeline.",
        )


class YoutubeExtractor(DocumentExtractor):
    """YouTube URL extractor (stub — wire yt-dlp + transcription later)."""

    source_type = "youtube"
    extensions = frozenset()
    url_patterns = ("youtube.com/watch", "youtu.be/", "youtube.com/shorts/")

    async def extract_bytes(self, file_bytes: bytes, filename: str) -> ExtractedContent:
        raise UnsupportedExtractionException("YouTube extraction requires a URL, not a file upload.")

    async def extract_url(self, url: str) -> ExtractedContent:
        raise UnsupportedExtractionException(
            "YouTube extraction is not enabled yet. Add yt-dlp + transcript/whisper pipeline."
        )
