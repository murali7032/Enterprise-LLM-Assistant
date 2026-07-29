"""Auto-diagnose alerts with read-only K8s evidence + advisory LLM hypothesis."""

from __future__ import annotations

import json
from typing import Any

from app.models.ops import AlertPayload, FindingHypothesis, OpsFinding
from app.observability.logger import logger
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.repositories.finding_repository import FindingStore
from app.services.llm_service import LLMService
from app.services.ops_notifier import OpsNotifier
from app.tools.kubernetes_tool import KubernetesTool


class OpsDiagnosisService:
    """Read-only investigation path for production alerts (no mutate)."""

    def __init__(
        self,
        k8s_tool: KubernetesTool,
        finding_store: FindingStore,
        notifier: OpsNotifier,
        llm_service: LLMService | None = None,
        prompt_builder: PromptBuilder | None = None,
        output_parser: OutputParser | None = None,
    ) -> None:
        self._k8s = k8s_tool
        self._store = finding_store
        self._notifier = notifier
        self._llm = llm_service
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._parser = output_parser or OutputParser()

    async def diagnose(self, alert: AlertPayload) -> OpsFinding:
        fingerprint = alert.resolve_fingerprint()
        evidence = await self._collect_evidence(alert)
        hypotheses, suggestions = await self._build_advisory(alert, evidence)

        finding = OpsFinding(
            fingerprint=fingerprint,
            alertname=alert.alertname,
            severity=alert.severity,
            namespace=alert.namespace,
            resource=alert.resource,
            resource_kind=alert.resource_kind,
            evidence=evidence,
            hypotheses=hypotheses,
            suggested_actions=suggestions,
            playbook_links=[],
            metadata={"labels": alert.labels, "annotations": alert.annotations},
        )
        stored = self._store.upsert(finding)
        # Only notify on first insert (not every duplicate alert)
        if not stored.notified:
            await self._notifier.notify(stored)
            self._store.mark_notified(stored.id)
        return stored

    async def _collect_evidence(self, alert: AlertPayload) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        ns = alert.namespace
        resource = alert.resource
        kind = (alert.resource_kind or "").lower()

        try:
            if resource and kind in {"pod", "pods"}:
                evidence.append(
                    await self._k8s.execute(
                        json.dumps({"action": "get", "kind": "pod", "name": resource, "namespace": ns})
                    )
                )
                evidence.append(
                    await self._k8s.execute(
                        json.dumps({"action": "events", "name": resource, "namespace": ns})
                    )
                )
                evidence.append(
                    await self._k8s.execute(
                        json.dumps({"action": "logs", "name": resource, "namespace": ns})
                    )
                )
            elif resource and kind in {"deployment", "deploy", "deployments"}:
                evidence.append(
                    await self._k8s.execute(
                        json.dumps(
                            {
                                "action": "get",
                                "kind": "deployment",
                                "name": resource,
                                "namespace": ns,
                            }
                        )
                    )
                )
                evidence.append(
                    await self._k8s.execute(
                        json.dumps({"action": "events", "name": resource, "namespace": ns})
                    )
                )
            else:
                evidence.append(
                    await self._k8s.execute(
                        json.dumps({"action": "list", "kind": "pods", "namespace": ns})
                    )
                )
                evidence.append(
                    await self._k8s.execute(json.dumps({"action": "events", "namespace": ns}))
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"evidence collection failed: {exc}")
            evidence.append({"error": str(exc)})
        return evidence

    async def _build_advisory(
        self,
        alert: AlertPayload,
        evidence: list[dict[str, Any]],
    ) -> tuple[list[FindingHypothesis], list[str]]:
        from app.core.config import settings

        suggestions = [
            "Inspect recent deployments and ConfigMap/Secret changes",
            "Check readiness/liveness probe failures and events",
            "Review pod logs for the failing container",
        ]
        if alert.resource and (alert.resource_kind or "").lower() in {"deployment", "deploy", "deployments"}:
            suggestions.append(f"Consider playbook: restart deploy {alert.resource} (requires approval)")
            suggestions.append(f"Consider playbook: scale deploy {alert.resource} N (requires approval)")

        if self._llm is None or not settings.OPS_USE_LLM_HYPOTHESIS:
            return (
                [
                    FindingHypothesis(
                        statement=(
                            f"Possible issue related to {alert.alertname} on "
                            f"{alert.resource_kind or 'resource'}/{alert.resource or 'unknown'}. "
                            "Treat as advisory until verified against evidence."
                        ),
                        confidence=0.4,
                        advisory=True,
                    )
                ],
                suggestions,
            )

        evidence_blob = json.dumps(evidence, default=str)[:6000]
        prompt = (
            "You are an SRE assistant. Given an alert and Kubernetes evidence, "
            "propose ONE concise root-cause HYPOTHESIS (not a proven fact) and 2-3 next checks.\n"
            "Respond as JSON: "
            '{"hypothesis":"...","confidence":0.0-1.0,"suggested_actions":["..."]}\n'
            f"Alert: {alert.alertname} severity={alert.severity}\n"
            f"Summary: {alert.summary or alert.description}\n"
            f"Resource: {alert.resource_kind}/{alert.resource} ns={alert.namespace}\n"
            f"Evidence:\n{evidence_blob}\n"
        )
        try:
            result = await self._llm.generate(prompt)
            text = self._parser.parse_text(result.content)
            data = json.loads(text) if text.strip().startswith("{") else {}
            if not data:
                # try extract JSON object
                start = text.find("{")
                end = text.rfind("}")
                if start >= 0 and end > start:
                    data = json.loads(text[start : end + 1])
            hyp = str(data.get("hypothesis") or text)[:500]
            conf = float(data.get("confidence", 0.5))
            conf = max(0.0, min(1.0, conf))
            extra = data.get("suggested_actions") or []
            if isinstance(extra, list):
                suggestions = [str(x) for x in extra][:5] or suggestions
            return (
                [FindingHypothesis(statement=hyp, confidence=conf, advisory=True)],
                suggestions,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"advisory LLM failed: {exc}")
            return (
                [
                    FindingHypothesis(
                        statement="Unable to generate LLM hypothesis; review evidence manually.",
                        confidence=0.2,
                        advisory=True,
                    )
                ],
                suggestions,
            )
