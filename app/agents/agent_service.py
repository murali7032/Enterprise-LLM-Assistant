from uuid import uuid4

from app.agents.executor import Executor
from app.agents.planner import Planner
from app.agents.tool_router import ToolRouter
from app.models.agent import AgentRequest, AgentResponse, AgentStep


class AgentService:
    """Agent framework with planner, executor, and observation loop."""

    def __init__(
        self,
        planner: Planner,
        executor: Executor,
        tool_router: ToolRouter,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._tool_router = tool_router

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Run the agent observation loop."""
        session_id = request.session_id or str(uuid4())
        observations: list[str] = []
        steps: list[AgentStep] = []
        answer = ""

        for _ in range(request.max_iterations):
            plan = await self._planner.plan(
                goal=request.goal,
                observations=observations,
                tools=self._tool_router.list_tools(),
            )
            thought = str(plan.get("thought", ""))
            action = str(plan.get("action", "finish"))
            tool_input = str(plan.get("input", ""))
            step = await self._executor.execute(thought, action, tool_input)
            steps.append(step)
            observations.append(step.observation)
            if action == "finish":
                answer = step.observation
                break

        if not answer and steps:
            answer = steps[-1].observation

        return AgentResponse(answer=answer, steps=steps, session_id=session_id)
