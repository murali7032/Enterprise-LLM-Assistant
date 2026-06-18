import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import AppException

T = TypeVar("T", bound=BaseModel)


class OutputParser:
    """Parse LLM outputs into structured formats."""

    def parse_text(self, content: str) -> str:
        """Return trimmed text output."""
        return content.strip()

    def parse_json(self, content: str) -> dict[str, Any]:
        """Parse JSON from raw or fenced model output."""
        cleaned = content.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AppException(f"Failed to parse JSON output: {exc}", status_code=422) from exc
        if not isinstance(parsed, dict):
            raise AppException("JSON output must be an object", status_code=422)
        return parsed

    def parse_model(self, content: str, model: type[T]) -> T:
        """Parse JSON output into a Pydantic model."""
        try:
            return model.model_validate(self.parse_json(content))
        except ValidationError as exc:
            raise AppException(f"Failed to validate model output: {exc}", status_code=422) from exc

    def parse_tool_response(self, content: str) -> dict[str, Any]:
        """Parse tool invocation output."""
        parsed = self.parse_json(content)
        if "action" not in parsed:
            raise AppException("Tool response must include an action", status_code=422)
        return parsed
