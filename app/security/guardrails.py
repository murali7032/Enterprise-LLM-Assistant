import re

from app.core.exceptions import GuardrailException

INJECTION_PATTERNS = [
    r"ignore (all|previous) instructions",
    r"disregard (the )?system prompt",
    r"reveal (your|the) (system|hidden) prompt",
    r"you are now",
    r"developer mode",
]


class PromptGuardrails:
    """Basic prompt injection guardrails."""

    def validate(self, text: str) -> None:
        """Validate user input against prompt injection patterns."""
        normalized = text.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, normalized):
                raise GuardrailException("Potential prompt injection detected")
