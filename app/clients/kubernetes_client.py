"""Kubernetes API client with in-cluster, kubeconfig, or mock auth."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppException
from app.observability.logger import logger


class KubernetesClient:
    """Thin wrapper around the Kubernetes Python client (read + allowlisted mutate)."""

    def __init__(self) -> None:
        self._mode = (settings.K8S_AUTH_MODE or "mock").lower()
        self._core = None
        self._apps = None
        self._ready = False
        self._init_clients()

    def _init_clients(self) -> None:
        if self._mode == "mock":
            self._ready = True
            return
        try:
            from kubernetes import client, config
        except ImportError as exc:
            raise AppException(
                "kubernetes package is required when K8S_AUTH_MODE is not mock",
                status_code=500,
            ) from exc

        try:
            if self._mode == "incluster":
                config.load_incluster_config()
            elif self._mode == "kubeconfig":
                config.load_kube_config(config_file=settings.KUBECONFIG_PATH or None)
            else:
                raise AppException(
                    f"Unknown K8S_AUTH_MODE '{self._mode}'", status_code=500
                )
            self._core = client.CoreV1Api()
            self._apps = client.AppsV1Api()
            self._ready = True
            logger.info("Kubernetes client initialized", mode=self._mode)
        except Exception as exc:  # noqa: BLE001 — surface as app error; keep API up
            logger.warning(f"Kubernetes client init failed: {exc}")
            self._mode = "mock"
            self._ready = True

    @property
    def mode(self) -> str:
        return self._mode

    def _mock_resource(self, kind: str, name: str, namespace: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "status": "Running",
            "replicas": 3,
            "ready_replicas": 3,
            "mock": True,
            "message": "Mock Kubernetes response (K8S_AUTH_MODE=mock)",
        }

    async def get_pod(self, name: str, namespace: str | None = None) -> dict[str, Any]:
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if self._mode == "mock" or self._core is None:
            return self._mock_resource("Pod", name, ns)
        pod = self._core.read_namespaced_pod(name=name, namespace=ns)
        return {
            "kind": "Pod",
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "node": pod.spec.node_name,
            "labels": dict(pod.metadata.labels or {}),
            "container_statuses": [
                {
                    "name": c.name,
                    "ready": c.ready,
                    "restart_count": c.restart_count,
                    "state": str(c.state),
                }
                for c in (pod.status.container_statuses or [])
            ],
        }

    async def list_pods(
        self, namespace: str | None = None, label_selector: str | None = None
    ) -> dict[str, Any]:
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if self._mode == "mock" or self._core is None:
            return {
                "kind": "PodList",
                "namespace": ns,
                "items": [self._mock_resource("Pod", "demo-pod-0", ns)],
                "mock": True,
            }
        pods = self._core.list_namespaced_pod(
            namespace=ns, label_selector=label_selector or None
        )
        return {
            "kind": "PodList",
            "namespace": ns,
            "items": [
                {
                    "name": p.metadata.name,
                    "phase": p.status.phase,
                    "restarts": sum(
                        (c.restart_count or 0)
                        for c in (p.status.container_statuses or [])
                    ),
                }
                for p in pods.items
            ],
        }

    async def get_deployment(
        self, name: str, namespace: str | None = None
    ) -> dict[str, Any]:
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if self._mode == "mock" or self._apps is None:
            return self._mock_resource("Deployment", name, ns)
        dep = self._apps.read_namespaced_deployment(name=name, namespace=ns)
        return {
            "kind": "Deployment",
            "name": dep.metadata.name,
            "namespace": dep.metadata.namespace,
            "replicas": dep.spec.replicas,
            "ready_replicas": dep.status.ready_replicas,
            "available_replicas": dep.status.available_replicas,
            "conditions": [
                {
                    "type": c.type,
                    "status": c.status,
                    "reason": c.reason,
                    "message": c.message,
                }
                for c in (dep.status.conditions or [])
            ],
        }

    async def list_events(
        self, namespace: str | None = None, involved_name: str | None = None
    ) -> dict[str, Any]:
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if self._mode == "mock" or self._core is None:
            return {
                "kind": "EventList",
                "namespace": ns,
                "items": [
                    {
                        "type": "Warning",
                        "reason": "Unhealthy",
                        "message": "Readiness probe failed (mock)",
                        "involved_object": involved_name or "demo-pod-0",
                    }
                ],
                "mock": True,
            }
        field_selector = (
            f"involvedObject.name={involved_name}" if involved_name else None
        )
        events = self._core.list_namespaced_event(
            namespace=ns, field_selector=field_selector
        )
        items = sorted(
            events.items,
            key=lambda e: e.last_timestamp
            or e.event_time
            or e.metadata.creation_timestamp,
            reverse=True,
        )
        return {
            "kind": "EventList",
            "namespace": ns,
            "items": [
                {
                    "type": e.type,
                    "reason": e.reason,
                    "message": e.message,
                    "count": e.count,
                    "involved_object": getattr(e.involved_object, "name", None),
                    "last_timestamp": str(e.last_timestamp or e.event_time or ""),
                }
                for e in items[:30]
            ],
        }

    async def get_pod_logs(
        self, name: str, namespace: str | None = None, tail_lines: int = 100
    ) -> dict[str, Any]:
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if self._mode == "mock" or self._core is None:
            return {
                "kind": "PodLog",
                "name": name,
                "namespace": ns,
                "logs": f"[mock] sample log lines for {name}\nERROR connection refused\n",
                "mock": True,
            }
        logs = self._core.read_namespaced_pod_log(
            name=name, namespace=ns, tail_lines=tail_lines
        )
        return {"kind": "PodLog", "name": name, "namespace": ns, "logs": logs}

    async def restart_deployment(
        self, name: str, namespace: str | None = None
    ) -> dict[str, Any]:
        """Mutating: trigger a rolling restart via annotation patch."""
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if self._mode == "mock" or self._apps is None:
            return {
                "kind": "DeploymentRestart",
                "name": name,
                "namespace": ns,
                "status": "restarted",
                "mock": True,
            }
        from datetime import UTC, datetime

        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "ops.enterprise-llm/restartedAt": datetime.now(
                                UTC
                            ).isoformat(),
                        }
                    }
                }
            }
        }
        self._apps.patch_namespaced_deployment(name=name, namespace=ns, body=body)
        return {
            "kind": "DeploymentRestart",
            "name": name,
            "namespace": ns,
            "status": "restarted",
        }

    async def scale_deployment(
        self, name: str, replicas: int, namespace: str | None = None
    ) -> dict[str, Any]:
        """Mutating: scale a deployment."""
        ns = namespace or settings.K8S_DEFAULT_NAMESPACE
        if replicas < 0 or replicas > settings.K8S_MAX_SCALE_REPLICAS:
            raise AppException(
                f"replicas must be between 0 and {settings.K8S_MAX_SCALE_REPLICAS}",
                status_code=400,
            )
        if self._mode == "mock" or self._apps is None:
            return {
                "kind": "DeploymentScale",
                "name": name,
                "namespace": ns,
                "replicas": replicas,
                "status": "scaled",
                "mock": True,
            }
        body = {"spec": {"replicas": replicas}}
        self._apps.patch_namespaced_deployment_scale(name=name, namespace=ns, body=body)
        return {
            "kind": "DeploymentScale",
            "name": name,
            "namespace": ns,
            "replicas": replicas,
            "status": "scaled",
        }

    def describe_from_query(self, query: str) -> dict[str, Any]:
        """Parse a simple query string into a describe request (sync helper for tool routing)."""
        # Formats: "pods", "pod/name", "deploy/name", "events", "logs/pod-name", "ns/foo pods"
        return {"raw": query.strip()}


def parse_k8s_query(query: str) -> dict[str, Any]:
    """Parse tool query into structured action.

    Supported examples:
      get pod my-pod
      list pods
      get deploy my-app
      events
      events my-pod
      logs my-pod
      restart deploy my-app
      scale deploy my-app 3
      {"action":"get","kind":"pod","name":"x","namespace":"default"}
    """
    text = query.strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    parts = text.split()
    if not parts:
        return {"action": "list", "kind": "pods"}

    action = parts[0].lower()
    rest = parts[1:]

    if action in {"get", "describe", "list", "events", "logs", "restart", "scale"}:
        pass
    else:
        # treat whole string as resource name for get
        return {"action": "get", "kind": "pod", "name": text}

    kind = rest[0].lower() if rest else "pods"
    name = None
    namespace = None
    replicas = None

    kind_aliases = {
        "pod": "pod",
        "pods": "pods",
        "deploy": "deployment",
        "deployment": "deployment",
        "deployments": "deployments",
        "event": "events",
        "events": "events",
        "log": "logs",
        "logs": "logs",
    }
    kind = kind_aliases.get(kind, kind)

    if action == "events":
        involved = (
            rest[0]
            if rest and rest[0].lower() not in kind_aliases
            else (rest[1] if len(rest) > 1 else None)
        )
        return {"action": "events", "kind": "events", "name": involved}
    if action == "logs":
        name = (
            rest[1]
            if len(rest) > 1 and rest[0].lower() in {"pod", "pods"}
            else (rest[0] if rest else None)
        )
        return {"action": "logs", "kind": "logs", "name": name}
    if action == "list":
        return {"action": "list", "kind": kind if kind.endswith("s") else f"{kind}s"}
    if action == "scale":
        # scale deploy name N
        if rest and rest[0].lower() in {"deploy", "deployment"}:
            name = rest[1] if len(rest) > 1 else None
            replicas = int(rest[2]) if len(rest) > 2 else None
        else:
            name = rest[0] if rest else None
            replicas = int(rest[1]) if len(rest) > 1 else None
        return {
            "action": "scale",
            "kind": "deployment",
            "name": name,
            "replicas": replicas,
        }
    if action == "restart":
        if rest and rest[0].lower() in {"deploy", "deployment"}:
            name = rest[1] if len(rest) > 1 else None
        else:
            name = rest[0] if rest else None
        return {"action": "restart", "kind": "deployment", "name": name}

    # get / describe
    if rest and rest[0].lower() in kind_aliases:
        kind = kind_aliases[rest[0].lower()]
        name = rest[1] if len(rest) > 1 else None
    elif rest:
        name = rest[0]
        kind = "pod"
    return {"action": action, "kind": kind, "name": name, "namespace": namespace}
