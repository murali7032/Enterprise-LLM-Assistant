import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.dependencies import get_ops_diagnosis_service
from app.main import app
from app.clients.kubernetes_client import KubernetesClient
from app.repositories.finding_repository import FindingStore
from app.services.ops_diagnosis_service import OpsDiagnosisService
from app.services.ops_notifier import OpsNotifier
from app.tools.kubernetes_tool import KubernetesTool


@pytest.fixture
def ops_client(monkeypatch) -> TestClient:
  monkeypatch.setattr(settings, "OPS_WEBHOOK_SECRET", "test-secret")
  monkeypatch.setattr(settings, "OPS_USE_LLM_HYPOTHESIS", False)
  store = FindingStore()
  service = OpsDiagnosisService(
    k8s_tool=KubernetesTool(client=KubernetesClient()),
    finding_store=store,
    notifier=OpsNotifier(),
    llm_service=None,
  )
  app.dependency_overrides[get_ops_diagnosis_service] = lambda: service
  with TestClient(app) as client:
    yield client
  app.dependency_overrides.pop(get_ops_diagnosis_service, None)


def test_ops_alerts_webhook(ops_client: TestClient) -> None:
  response = ops_client.post(
    "/api/v1/ops/alerts",
    headers={"X-Ops-Webhook-Secret": "test-secret"},
    json={
      "alerts": [
        {
          "labels": {"alertname": "HighErrorRate", "namespace": "default", "pod": "api-0"},
          "annotations": {"summary": "errors spiked"},
          "fingerprint": "fp-1",
        }
      ]
    },
  )
  assert response.status_code == 200
  body = response.json()
  assert len(body) == 1
  assert body[0]["finding"]["alertname"] == "HighErrorRate"
  assert body[0]["finding"]["evidence"]


def test_ops_alerts_rejects_bad_secret(ops_client: TestClient) -> None:
  response = ops_client.post(
    "/api/v1/ops/alerts",
    headers={"X-Ops-Webhook-Secret": "wrong"},
    json={"alertname": "X"},
  )
  assert response.status_code == 401
