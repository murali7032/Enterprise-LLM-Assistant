from fastapi import APIRouter, Depends

from app.agents.agent_service import AgentService
from app.dependencies import get_agent_service
from app.middleware.auth import require_auth_permission
from app.models.agent import AgentRequest, AgentResponse

router = APIRouter(prefix="/api/v1/agents", tags=["Agents"])


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    agent_service: AgentService = Depends(get_agent_service),
    _user: dict = Depends(require_auth_permission("agents")),
) -> AgentResponse:
    """Execute an agent for a goal."""
    return await agent_service.run(request)
