from typing import Any

from app.tools.base import Tool


class WeatherTool(Tool):
    """Return mock weather data for a location."""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Get current weather for a city"

    async def execute(self, query: str) -> dict[str, Any]:
        return {
            "location": query,
            "temperature_c": 22,
            "conditions": "partly cloudy",
        }
