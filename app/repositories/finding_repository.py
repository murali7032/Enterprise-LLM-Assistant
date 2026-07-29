"""In-memory finding and approval stores for ops agent v1."""

from __future__ import annotations

from threading import Lock
from typing import Any

from app.models.ops import OpsFinding, PendingApproval


class FindingStore:
    """Persist ops findings keyed by id; dedupe by fingerprint."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, OpsFinding] = {}
        self._by_fingerprint: dict[str, str] = {}

    def upsert(self, finding: OpsFinding) -> OpsFinding:
        with self._lock:
            existing_id = self._by_fingerprint.get(finding.fingerprint)
            if existing_id and existing_id in self._by_id:
                existing = self._by_id[existing_id]
                existing.evidence = finding.evidence or existing.evidence
                existing.hypotheses = finding.hypotheses or existing.hypotheses
                existing.suggested_actions = finding.suggested_actions or existing.suggested_actions
                existing.severity = finding.severity
                existing.status = finding.status
                existing.metadata = {**existing.metadata, **finding.metadata}
                return existing
            self._by_id[finding.id] = finding
            self._by_fingerprint[finding.fingerprint] = finding.id
            return finding

    def get(self, finding_id: str) -> OpsFinding | None:
        with self._lock:
            return self._by_id.get(finding_id)

    def list(self, limit: int = 50) -> list[OpsFinding]:
        with self._lock:
            items = sorted(self._by_id.values(), key=lambda f: f.created_at, reverse=True)
            return items[:limit]

    def mark_notified(self, finding_id: str) -> None:
        with self._lock:
            finding = self._by_id.get(finding_id)
            if finding:
                finding.notified = True


class ApprovalStore:
    """Track pending mutate approvals for HITL chat/agent flows."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: dict[str, PendingApproval] = {}
        self._approved: set[str] = set()

    def put(self, approval: PendingApproval) -> PendingApproval:
        with self._lock:
            self._pending[approval.approval_id] = approval
            return approval

    def get(self, approval_id: str) -> PendingApproval | None:
        with self._lock:
            return self._pending.get(approval_id)

    def approve(self, approval_id: str) -> PendingApproval | None:
        with self._lock:
            item = self._pending.get(approval_id)
            if item is None:
                return None
            self._approved.add(approval_id)
            return item

    def is_approved(self, approval_id: str) -> bool:
        with self._lock:
            return approval_id in self._approved

    def list_pending(self, session_id: str | None = None) -> list[PendingApproval]:
        with self._lock:
            items = list(self._pending.values())
            if session_id:
                items = [i for i in items if i.session_id == session_id]
            return items

    def consume_approved_payload(self, approval_id: str) -> dict[str, Any] | None:
        """Return approved tool args with approved=True, or None."""
        with self._lock:
            if approval_id not in self._approved:
                return None
            item = self._pending.get(approval_id)
            if item is None:
                return None
            return {
                "action": item.action,
                "approved": True,
                **item.args,
            }
