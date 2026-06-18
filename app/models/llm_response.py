from pydantic import BaseModel, Field


class LLMResult(BaseModel):
    """Normalized LLM generation result."""

    content: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = Field(default=0.0, ge=0.0)
