import json
from uuid import uuid4

from app.agents.executor import Executor
from app.agents.planner import Planner
from app.agents.tool_router import ToolRouter
from app.models.agent import AgentRequest, AgentResponse, AgentStep
from app.models.ops import PendingApproval
from app.repositories.finding_repository import ApprovalStore
from app.tools.k8s_playbook_tool import PENDING_APPROVAL_MARKER, K8sPlaybookTool


class AgentService:
    """Agent framework with planner, executor, observation loop, and HITL mutate gates."""

    def __init__(
        self,
        planner: Planner,
        executor: Executor,
        tool_router: ToolRouter,
        approval_store: ApprovalStore | None = None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._tool_router = tool_router
        self._approvals = approval_store or ApprovalStore()

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Run the agent observation loop."""
        session_id = request.session_id or str(uuid4())
        observations: list[str] = []
        steps: list[AgentStep] = []
        pending: list[PendingApproval] = []
        answer = ""

        # Pre-load approved mutate payloads into executor context via query rewrite helpers
        approved_ids = set(request.approved_action_ids or [])

        for _ in range(request.max_iterations):
            plan = await self._planner.plan(
                goal=request.goal,
                observations=observations,
                tools=self._tool_router.list_tools(),
            )
            thought = str(plan.get("thought", ""))
            action = str(plan.get("action", "finish"))
            tool_input = str(plan.get("input", ""))

            if action == "k8s_playbook":
                tool_input, new_pending = self._prepare_playbook_input(
                    tool_input,
                    approved_ids=approved_ids,
                    session_id=session_id,
                    thought=thought,
                )
                if new_pending:
                    pending.append(new_pending)
                    step = AgentStep(
                        thought=thought,
                        action=action,
                        observation=json.dumps(
                            {
                                "status": PENDING_APPROVAL_MARKER,
                                "approval_id": new_pending.approval_id,
                                "message": new_pending.reason,
                                "proposed": {
                                    "tool": new_pending.tool,
                                    "action": new_pending.action,
                                    "args": new_pending.args,
                                },
                            }
                        ),
                    )
                    steps.append(step)
                    observations.append(step.observation)
                    answer = (
                        "A mutating Kubernetes playbook requires your approval before it can run. "
                        f"Approve action {new_pending.approval_id} to continue."
                    )
                    break

            step = await self._executor.execute(thought, action, tool_input)
            steps.append(step)
            observations.append(step.observation)

            # Detect mutate tool returning pending without going through prepare path
            if PENDING_APPROVAL_MARKER in step.observation and action == "k8s_playbook":
                try:
                    data = json.loads(step.observation.replace("'", '"'))
                except json.JSONDecodeError:
                    data = {}
                if isinstance(data, dict) and data.get("status") == PENDING_APPROVAL_MARKER:
                    approval = PendingApproval(
                        tool="k8s_playbook",
                        action=str(data.get("proposed_action") or "unknown"),
                        args=dict(data.get("args") or {}),
                        reason=str(data.get("message") or "Approval required"),
                        session_id=session_id,
                    )
                    self._approvals.put(approval)
                    pending.append(approval)
                    answer = (
                        "A mutating Kubernetes playbook requires your approval before it can run. "
                        f"Approve action {approval.approval_id} to continue."
                    )
                    break

            if action == "finish":
                answer = step.observation
                break

        if not answer and steps:
            answer = steps[-1].observation

        return AgentResponse(
            answer=answer,
            steps=steps,
            session_id=session_id,
            pending_approvals=pending,
        )

    async def approve_and_execute(self, approval_id: str) -> dict:
        """Mark approval and execute the playbook immediately."""
        item = self._approvals.approve(approval_id)
        if item is None:
            return {"status": "not_found", "approval_id": approval_id}
        payload = self._approvals.consume_approved_payload(approval_id)
        if payload is None:
            return {"status": "not_approved", "approval_id": approval_id}
        tool = self._tool_router._tools.get("k8s_playbook")  # noqa: SLF001
        if not isinstance(tool, K8sPlaybookTool):
            # Still try execute via router
            result = await self._tool_router.execute("k8s_playbook", json.dumps(payload))
            return {"status": "executed", "approval_id": approval_id, "result": result}
        result = await tool.execute(json.dumps(payload))
        return {"status": "executed", "approval_id": approval_id, "result": result}

    def _prepare_playbook_input(
        self,
        tool_input: str,
        *,
        approved_ids: set[str],
        session_id: str,
        thought: str,
    ) -> tuple[str, PendingApproval | None]:
        """If not approved, register pending and signal caller to stop; else inject approved=true."""
        playbook = K8sPlaybookTool()
        parsed = playbook._parse(tool_input)  # noqa: SLF001
        action = str(parsed.get("action") or "unknown")
        args = {k: v for k, v in parsed.items() if k not in {"approved", "action"}}

        # Match against previously approved pending items listed by the client
        for approval_id in approved_ids:
            pending_item = self._approvals.get(approval_id)
            if pending_item and pending_item.action == action and pending_item.args == args:
                self._approvals.approve(approval_id)
                payload = {"action": action, "approved": True, **args}
                return json.dumps(payload), None
            # Also allow approving by id alone (UI approve-then-rerun with same goal)
            if pending_item and approval_id in approved_ids:
                self._approvals.approve(approval_id)
                payload = {
                    "action": pending_item.action,
                    "approved": True,
                    **pending_item.args,
                }
                return json.dumps(payload), None

        approval = PendingApproval(
            tool="k8s_playbook",
            action=action,
            args=args,
            reason=thought or "Mutating playbook requires approval",
            session_id=session_id,
        )
        self._approvals.put(approval)
        return tool_input, approval
