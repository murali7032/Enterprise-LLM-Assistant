from app.core.exceptions import ToolExecutionException
from app.tools.base import Tool


class ToolRouter:
    """Route agent actions to registered tools."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def list_tools(self) -> list[str]:
        """Return available tool names."""
        return sorted(self._tools.keys())

    async def execute(self, action: str, query: str) -> dict:
        """Execute a tool by name."""
        tool = self._tools.get(action)
        if tool is None:
            raise ToolExecutionException(f"Unknown tool: {action}")
        return await tool.execute(query)
