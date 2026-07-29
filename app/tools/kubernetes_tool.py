from typing import Any

from app.clients.kubernetes_client import KubernetesClient, parse_k8s_query
from app.core.exceptions import AppException
from app.tools.base import Tool

# Read-only actions allowed without HITL approval.
READ_ACTIONS = {"get", "describe", "list", "events", "logs"}


class KubernetesTool(Tool):
    """Inspect Kubernetes resources (read-only get/list/describe/logs/events)."""

    def __init__(self, client: KubernetesClient | None = None) -> None:
        self._client = client or KubernetesClient()

    @property
    def name(self) -> str:
        return "kubernetes"

    @property
    def description(self) -> str:
        return (
            "Read-only Kubernetes inspect. "
            "Examples: 'get pod NAME', 'list pods', 'get deploy NAME', 'events NAME', 'logs POD'"
        )

    async def execute(self, query: str) -> dict[str, Any]:
        parsed = parse_k8s_query(query)
        action = str(parsed.get("action", "get")).lower()
        if action not in READ_ACTIONS:
            raise AppException(
                f"Action '{action}' is mutating; use playbook tools with approval",
                status_code=400,
            )
        kind = str(parsed.get("kind", "pod")).lower()
        name = parsed.get("name")
        namespace = parsed.get("namespace")
        if isinstance(namespace, str) and not namespace.strip():
            namespace = None

        if action in {"get", "describe"}:
            if kind in {"pod", "pods"}:
                if not name:
                    return await self._client.list_pods(namespace=namespace)
                return await self._client.get_pod(str(name), namespace=namespace)
            if kind in {"deployment", "deploy", "deployments"}:
                if not name:
                    raise AppException("deployment name required", status_code=400)
                return await self._client.get_deployment(str(name), namespace=namespace)
            raise AppException(f"Unsupported kind for get: {kind}", status_code=400)

        if action == "list":
            if "pod" in kind:
                return await self._client.list_pods(namespace=namespace)
            raise AppException(f"Unsupported kind for list: {kind}", status_code=400)

        if action == "events":
            return await self._client.list_events(namespace=namespace, involved_name=str(name) if name else None)

        if action == "logs":
            if not name:
                raise AppException("pod name required for logs", status_code=400)
            return await self._client.get_pod_logs(str(name), namespace=namespace)

        raise AppException(f"Unsupported action: {action}", status_code=400)
