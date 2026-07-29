from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AppException
from app.dependencies import get_finding_store, get_ops_diagnosis_service
from app.middleware.auth import require_auth_permission
from app.models.ops import AlertPayload, AlertmanagerWebhook, OpsFinding
from app.repositories.finding_repository import FindingStore
from app.services.ops_diagnosis_service import OpsDiagnosisService

router = APIRouter(prefix="/api/v1/ops", tags=["Ops"])


class DiagnoseResponse(BaseModel):
    finding: OpsFinding
    deduplicated: bool = False


def _normalize_alertmanager(body: AlertmanagerWebhook) -> list[AlertPayload]:
    alerts: list[AlertPayload] = []
    for raw in body.alerts:
        labels = {**(body.commonLabels or {}), **(raw.get("labels") or {})}
        annotations = {
            **(body.commonAnnotations or {}),
            **(raw.get("annotations") or {}),
        }
        alerts.append(
            AlertPayload(
                alertname=str(labels.get("alertname") or "UnknownAlert"),
                severity=str(labels.get("severity") or "warning"),
                summary=str(annotations.get("summary") or ""),
                description=str(annotations.get("description") or ""),
                namespace=labels.get("namespace"),
                resource=labels.get("pod")
                or labels.get("deployment")
                or labels.get("resource"),
                resource_kind=(
                    "pod"
                    if labels.get("pod")
                    else (
                        "deployment"
                        if labels.get("deployment")
                        else labels.get("resource_kind")
                    )
                ),
                labels={str(k): str(v) for k, v in labels.items()},
                annotations={str(k): str(v) for k, v in annotations.items()},
                fingerprint=raw.get("fingerprint"),
                starts_at=raw.get("startsAt"),
                raw=raw,
            )
        )
    return alerts


@router.post("/alerts", response_model=list[DiagnoseResponse])
async def ingest_alerts(
    request: Request,
    diagnosis: OpsDiagnosisService = Depends(get_ops_diagnosis_service),
    store: FindingStore = Depends(get_finding_store),
) -> list[DiagnoseResponse]:
    """Ingest Alertmanager webhook or a single normalized alert. Optional shared secret header."""
    _verify_webhook_secret(request)
    payload = await request.json()

    if isinstance(payload, dict) and "alerts" in payload:
        alerts = _normalize_alertmanager(AlertmanagerWebhook.model_validate(payload))
    elif isinstance(payload, dict) and "alertname" in payload:
        alerts = [AlertPayload.model_validate(payload)]
    else:
        raise AppException(
            "Expected Alertmanager webhook or AlertPayload JSON", status_code=400
        )

    results: list[DiagnoseResponse] = []
    for alert in alerts:
        existing = None
        fp = alert.resolve_fingerprint()
        for item in store.list(limit=200):
            if item.fingerprint == fp:
                existing = item
                break
        finding = await diagnosis.diagnose(alert)
        results.append(
            DiagnoseResponse(
                finding=finding,
                deduplicated=existing is not None and existing.id == finding.id,
            )
        )
    return results


@router.get("/findings", response_model=list[OpsFinding])
async def list_findings(
    limit: int = 50,
    store: FindingStore = Depends(get_finding_store),
    _user: dict = Depends(require_auth_permission("ops")),
) -> list[OpsFinding]:
    """List recent ops findings."""
    return store.list(limit=min(limit, 200))


@router.get("/findings/{finding_id}", response_model=OpsFinding)
async def get_finding(
    finding_id: str,
    store: FindingStore = Depends(get_finding_store),
    _user: dict = Depends(require_auth_permission("ops")),
) -> OpsFinding:
    finding = store.get(finding_id)
    if finding is None:
        raise AppException("Finding not found", status_code=404)
    return finding


class SimpleAlertRequest(BaseModel):
    """Convenience body for manual / demo alerts."""

    alertname: str
    severity: str = "warning"
    summary: str = ""
    namespace: str | None = None
    resource: str | None = None
    resource_kind: str | None = "pod"
    labels: dict[str, str] = Field(default_factory=dict)


@router.post("/alerts/simple", response_model=DiagnoseResponse)
async def ingest_simple_alert(
    body: SimpleAlertRequest,
    request: Request,
    diagnosis: OpsDiagnosisService = Depends(get_ops_diagnosis_service),
    _user: dict = Depends(require_auth_permission("ops")),
) -> DiagnoseResponse:
    """Authenticated helper to fire a single alert for demos."""
    _verify_webhook_secret(request)
    alert = AlertPayload(
        alertname=body.alertname,
        severity=body.severity,
        summary=body.summary,
        namespace=body.namespace,
        resource=body.resource,
        resource_kind=body.resource_kind,
        labels=body.labels,
    )
    finding = await diagnosis.diagnose(alert)
    return DiagnoseResponse(finding=finding)


def _verify_webhook_secret(request: Request) -> None:
    expected = settings.OPS_WEBHOOK_SECRET.strip()
    if not expected:
        return
    provided = request.headers.get("X-Ops-Webhook-Secret") or ""
    if provided != expected:
        raise AppException("Invalid ops webhook secret", status_code=401)
