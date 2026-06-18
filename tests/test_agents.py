import pytest

from app.agents.agent_service import AgentService
from app.agents.executor import Executor
from app.agents.tool_router import ToolRouter
from app.models.agent import AgentRequest
from app.tools.weather_tool import WeatherTool


@pytest.mark.asyncio
async def test_weather_tool() -> None:
  tool = WeatherTool()
  result = await tool.execute("London")
  assert result["location"] == "London"


@pytest.mark.asyncio
async def test_agent_service_finish_flow(monkeypatch) -> None:
  class StubPlanner:
    async def plan(self, goal, observations, tools):
      if not observations:
        return {"thought": "check weather", "action": "weather", "input": "London"}
      return {"thought": "done", "action": "finish", "input": "It is sunny"}

  service = AgentService(
    planner=StubPlanner(),
    executor=Executor(tool_router=ToolRouter([WeatherTool()])),
    tool_router=ToolRouter([WeatherTool()]),
  )
  response = await service.run(AgentRequest(goal="check weather"))
  assert "sunny" in response.answer.lower()
  assert len(response.steps) >= 2
