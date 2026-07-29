"""Notify developers of ops findings (log + optional Slack webhook)."""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.models.ops import OpsFinding
from app.observability.logger import logger


class OpsNotifier:
    """Send finding notifications. Kafka is out of scope for v1."""

    async def notify(self, finding: OpsFinding) -> None:
        message = self._format(finding)
        logger.info(
            "ops_finding_notification",
            finding_id=finding.id,
            fingerprint=finding.fingerprint,
            alertname=finding.alertname,
        )
        logger.info(message)

        webhook = settings.OPS_SLACK_WEBHOOK_URL.strip()
        if webhook:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(webhook, json={"text": message})
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Slack notify failed: {exc}")

    def _format(self, finding: OpsFinding) -> str:
        hyp = finding.hypotheses[0].statement if finding.hypotheses else "No hypothesis"
        conf = finding.hypotheses[0].confidence if finding.hypotheses else 0.0
        actions = "; ".join(finding.suggested_actions[:5]) or "None"
        return (
            f"[Ops Finding] {finding.alertname} ({finding.severity})\n"
            f"id={finding.id} fingerprint={finding.fingerprint}\n"
            f"resource={finding.resource_kind}/{finding.resource} ns={finding.namespace}\n"
            f"hypothesis (advisory, conf={conf:.2f}): {hyp}\n"
            f"suggested: {actions}\n"
            f"evidence_count={len(finding.evidence)}"
        )
