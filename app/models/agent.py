from typing import Any

from pydantic import BaseModel, Field

from app.models.ops import PendingApproval


class AgentRequest(BaseModel):
    """Request to run an agent."""

    goal: str = Field(..., min_length=1)
    session_id: str | None = None
    max_iterations: int = Field(default=5, ge=1, le=20)
    # After HITL approve, client re-runs with these approval ids so mutate tools may execute.
    approved_action_ids: list[str] = Field(default_factory=list)


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
    pending_approvals: list[PendingApproval] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentApproveRequest(BaseModel):
    """Approve a pending mutating playbook action."""

    approval_id: str
    session_id: str | None = None


class AgentApproveResponse(BaseModel):
    approval_id: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
