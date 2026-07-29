from fastapi import APIRouter, Depends

from app.agents.agent_service import AgentService
from app.dependencies import get_agent_service
from app.middleware.auth import require_auth_permission
from app.models.agent import (
    AgentApproveRequest,
    AgentApproveResponse,
    AgentRequest,
    AgentResponse,
)

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    agent_service: AgentService = Depends(get_agent_service),
    _user: dict = Depends(require_auth_permission("agents")),
) -> AgentResponse:
    """Execute an agent for a goal. Mutating playbooks return pending_approvals."""
    return await agent_service.run(request)


@router.post("/approve", response_model=AgentApproveResponse)
async def approve_agent_action(
    body: AgentApproveRequest,
    agent_service: AgentService = Depends(get_agent_service),
    _user: dict = Depends(require_auth_permission("agents")),
) -> AgentApproveResponse:
    """Approve and execute a pending mutating playbook."""
    result = await agent_service.approve_and_execute(body.approval_id)
    return AgentApproveResponse(
        approval_id=body.approval_id,
        status=str(result.get("status")),
        result=result.get("result") or {},
    )
