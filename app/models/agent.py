from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request to run an agent."""

    goal: str = Field(..., min_length=1)
    session_id: str | None = None
    max_iterations: int = Field(default=5, ge=1, le=20)


class AgentStep(BaseModel):
    """A single agent execution step."""

    thought: str
    action: str
    observation: str


class AgentResponse(BaseModel):
    """Agent execution result."""

    answer: str
    steps: list[AgentStep] = Field(default_factory=list)
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
