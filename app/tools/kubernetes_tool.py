from typing import Any

from app.tools.base import Tool


class KubernetesTool(Tool):
    """Return mock Kubernetes cluster information."""

    @property
    def name(self) -> str:
        return "kubernetes"

    @property
    def description(self) -> str:
        return "Inspect Kubernetes resources"

    async def execute(self, query: str) -> dict[str, Any]:
        return {
            "resource": query,
            "status": "Running",
            "replicas": 3,
        }
