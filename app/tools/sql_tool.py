from typing import Any

from app.tools.base import Tool


class SQLTool(Tool):
    """Execute read-only SQL queries against a mock dataset."""

    @property
    def name(self) -> str:
        return "sql"

    @property
    def description(self) -> str:
        return "Run a read-only SQL query"

    async def execute(self, query: str) -> dict[str, Any]:
        return {
            "query": query,
            "rows": [{"id": 1, "name": "example"}],
            "row_count": 1,
        }
