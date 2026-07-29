"""Allowlisted mutating K8s playbooks that require explicit approval."""

from __future__ import annotations

import json
from typing import Any

from app.clients.kubernetes_client import KubernetesClient, parse_k8s_query
from app.core.exceptions import AppException
from app.tools.base import Tool

# Marker returned when a mutate is requested without approval.
PENDING_APPROVAL_MARKER = "PENDING_APPROVAL"


class K8sPlaybookTool(Tool):
    """Mutating playbooks: restart_deployment, scale_deployment — require approval."""

    MUTATING = True

    def __init__(self, client: KubernetesClient | None = None) -> None:
        self._client = client or KubernetesClient()

    @property
    def name(self) -> str:
        return "k8s_playbook"

    @property
    def description(self) -> str:
        return (
            "Mutating Kubernetes playbooks (REQUIRE human approval). "
            "Examples: 'restart deploy my-app', 'scale deploy my-app 3'. "
            "Do not call unless the user approved."
        )

    async def execute(self, query: str) -> dict[str, Any]:
        """Execute only when query JSON includes approved=true (set by agent after HITL)."""
        payload = self._parse(query)
        if not payload.get("approved"):
            return {
                "status": PENDING_APPROVAL_MARKER,
                "tool": self.name,
                "proposed_action": payload.get("action"),
                "args": {k: v for k, v in payload.items() if k not in {"approved", "action"}},
                "message": "Mutating action requires explicit user approval",
            }

        action = str(payload.get("action", "")).lower()
        name = payload.get("name")
        namespace = payload.get("namespace")
        if not name:
            raise AppException("playbook requires deployment name", status_code=400)

        if action == "restart":
            return await self._client.restart_deployment(str(name), namespace=namespace)
        if action == "scale":
            replicas = payload.get("replicas")
            if replicas is None:
                raise AppException("scale requires replicas", status_code=400)
            return await self._client.scale_deployment(str(name), int(replicas), namespace=namespace)

        raise AppException(
            f"Unknown playbook action '{action}'. Allowed: restart, scale",
            status_code=400,
        )

    def _parse(self, query: str) -> dict[str, Any]:
        text = query.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        parsed = parse_k8s_query(text)
        action = str(parsed.get("action", "")).lower()
        if action not in {"restart", "scale"}:
            # default interpret "restart X" already handled by parse_k8s_query
            if text.lower().startswith("restart"):
                action = "restart"
            elif text.lower().startswith("scale"):
                action = "scale"
        return {
            "action": action,
            "name": parsed.get("name"),
            "namespace": parsed.get("namespace"),
            "replicas": parsed.get("replicas"),
            "approved": False,
        }
