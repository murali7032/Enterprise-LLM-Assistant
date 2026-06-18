import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure structured application logging."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    return logging.getLogger("enterprise-llm")


logger = setup_logging()


def log_with_context(logger_instance: logging.Logger, message: str, **context: Any) -> None:
    """Log a message with optional structured context."""
    if context:
        context_str = " ".join(f"{key}={value}" for key, value in context.items())
        logger_instance.info("%s | %s", message, context_str)
    else:
        logger_instance.info(message)
