import logging
from typing import Any

from app.core.config import settings


class StructuredLogger:
    """Structured logger with request and correlation context."""

    def __init__(self, name: str = "enterprise-llm") -> None:
        self._logger = logging.getLogger(name)

    def bind(self, **context: Any) -> "StructuredLogger":
        """Return a logger wrapper with bound context."""
        bound = StructuredLogger(self._logger.name)
        bound._context = {**getattr(self, "_context", {}), **context}
        return bound

    def _format(self, message: str) -> str:
        context = getattr(self, "_context", {})
        if not context:
            return message
        suffix = " ".join(f"{key}={value}" for key, value in context.items())
        return f"{message} | {suffix}"

    def info(self, message: str, **extra: Any) -> None:
        self._logger.info(self._format(message), extra=extra)

    def warning(self, message: str, **extra: Any) -> None:
        self._logger.warning(self._format(message), extra=extra)

    def error(self, message: str, **extra: Any) -> None:
        self._logger.error(self._format(message), extra=extra)


def get_logger(name: str = "enterprise-llm") -> StructuredLogger:
    """Create a structured logger."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    return StructuredLogger(name)


logger = get_logger()
