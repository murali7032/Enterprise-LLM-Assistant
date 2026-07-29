"""Ops / incident finding models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertPayload(BaseModel):
    """Normalized alert (Alertmanager-compatible subset + simple form)."""

    alertname: str = Field(..., min_length=1)
    severity: str = "warning"
    summary: str = ""
    description: str = ""
    namespace: str | None = None
    resource: str | None = None
    resource_kind: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    fingerprint: str | None = None
    starts_at: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    def resolve_fingerprint(self) -> str:
        if self.fingerprint:
            return self.fingerprint
        parts = [
            self.alertname,
            self.namespace or "",
            self.resource_kind or "",
            self.resource or "",
        ]
        return "|".join(parts)


class AlertmanagerWebhook(BaseModel):
    """Subset of Alertmanager webhook JSON."""

    version: str | None = None
    status: str | None = None
    receiver: str | None = None
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str | None = None


class FindingHypothesis(BaseModel):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    advisory: bool = True


class OpsFinding(BaseModel):
    """Structured diagnosis output — evidence first, LLM text advisory."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    fingerprint: str
    alertname: str
    severity: str = "warning"
    namespace: str | None = None
    resource: str | None = None
    resource_kind: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[FindingHypothesis] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    playbook_links: list[str] = Field(default_factory=list)
    status: str = "open"  # open | acknowledged | resolved
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    notified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingApproval(BaseModel):
    """HITL gate for a mutating playbook action."""

    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    tool: str
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    session_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
