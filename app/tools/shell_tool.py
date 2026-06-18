from typing import Any

from app.tools.base import Tool


class ShellTool(Tool):
    """Simulate shell command execution for safe demos."""

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "Execute an approved shell command"

    async def execute(self, query: str) -> dict[str, Any]:
        allowed = {"pwd", "whoami", "date"}
        command = query.strip()
        if command not in allowed:
            return {"command": command, "stdout": "", "stderr": "Command not allowed", "exit_code": 1}
        return {"command": command, "stdout": f"simulated output for {command}", "stderr": "", "exit_code": 0}
