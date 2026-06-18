from app.agents.tool_router import ToolRouter
from app.models.agent import AgentStep


class Executor:
    """Execute planned agent actions."""

    def __init__(self, tool_router: ToolRouter) -> None:
        self._tool_router = tool_router

    async def execute(self, thought: str, action: str, query: str) -> AgentStep:
        """Execute a tool action and return an observation step."""
        if action == "finish":
            return AgentStep(thought=thought, action=action, observation=query)
        observation = await self._tool_router.execute(action, query)
        return AgentStep(thought=thought, action=action, observation=str(observation))
