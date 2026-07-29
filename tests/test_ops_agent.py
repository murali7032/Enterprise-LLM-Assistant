import json

import pytest

from app.agents.agent_service import AgentService
from app.agents.executor import Executor
from app.agents.tool_router import ToolRouter
from app.clients.kubernetes_client import KubernetesClient, parse_k8s_query
from app.models.agent import AgentRequest
from app.models.ops import AlertPayload
from app.repositories.finding_repository import ApprovalStore, FindingStore
from app.services.ops_diagnosis_service import OpsDiagnosisService
from app.services.ops_notifier import OpsNotifier
from app.tools.k8s_playbook_tool import PENDING_APPROVAL_MARKER, K8sPlaybookTool
from app.tools.kubernetes_tool import KubernetesTool
from app.tools.weather_tool import WeatherTool


def test_parse_k8s_query_get_pod() -> None:
    parsed = parse_k8s_query("get pod demo")
    assert parsed["action"] == "get"
    assert parsed["name"] == "demo"


def test_parse_k8s_query_scale() -> None:
    parsed = parse_k8s_query("scale deploy my-app 3")
    assert parsed["action"] == "scale"
    assert parsed["name"] == "my-app"
    assert parsed["replicas"] == 3


@pytest.mark.asyncio
async def test_kubernetes_tool_mock_list_pods() -> None:
    tool = KubernetesTool(client=KubernetesClient())
    result = await tool.execute("list pods")
    assert result["kind"] == "PodList"
    assert result.get("mock") is True


@pytest.mark.asyncio
async def test_kubernetes_tool_rejects_mutate() -> None:
    tool = KubernetesTool(client=KubernetesClient())
    with pytest.raises(Exception):
        await tool.execute("restart deploy my-app")


@pytest.mark.asyncio
async def test_playbook_requires_approval() -> None:
    tool = K8sPlaybookTool(client=KubernetesClient())
    result = await tool.execute("restart deploy my-app")
    assert result["status"] == PENDING_APPROVAL_MARKER


@pytest.mark.asyncio
async def test_playbook_runs_when_approved() -> None:
    tool = K8sPlaybookTool(client=KubernetesClient())
    result = await tool.execute(
        json.dumps({"action": "restart", "name": "my-app", "approved": True})
    )
    assert result["status"] == "restarted"


@pytest.mark.asyncio
async def test_ops_diagnosis_without_llm() -> None:
    store = FindingStore()
    service = OpsDiagnosisService(
        k8s_tool=KubernetesTool(client=KubernetesClient()),
        finding_store=store,
        notifier=OpsNotifier(),
        llm_service=None,
    )
    finding = await service.diagnose(
        AlertPayload(
            alertname="PodCrashLooping",
            severity="critical",
            summary="pod restarting",
            namespace="default",
            resource="demo-pod",
            resource_kind="pod",
        )
    )
    assert finding.alertname == "PodCrashLooping"
    assert finding.hypotheses
    assert finding.hypotheses[0].advisory is True
    assert finding.evidence
    # dedupe
    again = await service.diagnose(
        AlertPayload(
            alertname="PodCrashLooping",
            namespace="default",
            resource="demo-pod",
            resource_kind="pod",
        )
    )
    assert again.id == finding.id


@pytest.mark.asyncio
async def test_agent_playbook_pending_approval(monkeypatch) -> None:
    class StubPlanner:
        async def plan(self, goal, observations, tools):
            return {
                "thought": "restart it",
                "action": "k8s_playbook",
                "input": "restart deploy demo",
            }

    approvals = ApprovalStore()
    client = KubernetesClient()
    router = ToolRouter(
        tools=[
            WeatherTool(),
            KubernetesTool(client=client),
            K8sPlaybookTool(client=client),
        ]
    )
    service = AgentService(
        planner=StubPlanner(),
        executor=Executor(tool_router=router),
        tool_router=router,
        approval_store=approvals,
    )
    response = await service.run(AgentRequest(goal="restart the demo deployment"))
    assert response.pending_approvals
    approval_id = response.pending_approvals[0].approval_id
    executed = await service.approve_and_execute(approval_id)
    assert executed["status"] == "executed"
    assert executed["result"]["status"] == "restarted"
