import pytest
from pathlib import Path

import control_center.main as main_module
from control_center.main import store
from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionLayerHealthResponse,
    DiscussionPrompt,
)
from control_center.services import WorkflowScheduler
from control_center.services.metrics_alert_policy_store import MetricsAlertPolicyStore
from control_center.services.workflow_engine import WorkflowEngine


class TestActionLayerClient:
    async def get_health(self) -> ActionLayerHealthResponse:
        return ActionLayerHealthResponse(
            status="ok",
            layer="action",
            transport="http",
        )

    async def execute(self, payload: ActionExecuteRequest) -> ActionExecuteResponse:
        selected_agent = payload.agent or "coding-agent"
        lowered = payload.text.lower()
        if (
            "role=module-dev" in lowered
            and "module=needs-discussion" in lowered
            and "discussion_resolved=true" not in lowered
        ):
            return ActionExecuteResponse(
                status="needs_discussion",
                summary="need discussion before implementation",
                agent=selected_agent,
                trace_id="act_test_discussion",
                discussion=DiscussionPrompt(
                    question="Pick implementation strategy",
                    options=["option-a", "option-b"],
                    recommendation="option-a",
                    impact="changes module behavior",
                    fingerprint="needs-discussion-module-dev",
                ),
            )
        if "fail" in lowered or "error" in lowered:
            return ActionExecuteResponse(
                status="failed",
                summary="mock execution failed by command content",
                agent=selected_agent,
                trace_id="act_test_fail",
            )
        return ActionExecuteResponse(
            status="success",
            summary="mock execution completed",
            agent=selected_agent,
            trace_id="act_test_success",
        )


@pytest.fixture(autouse=True)
def reset_inmemory_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    temp_root = tmp_path / "wherecode-test"
    temp_root.mkdir(parents=True, exist_ok=True)
    policy_store = MetricsAlertPolicyStore(
        str(temp_root / "metrics_alert_policy.json"),
        str(temp_root / "metrics_alert_policy_audit.jsonl"),
    )
    monkeypatch.setattr(main_module, "AUTH_ENABLED", False)
    monkeypatch.setattr(main_module, "action_layer", TestActionLayerClient())
    monkeypatch.setattr(main_module, "workflow_scheduler", WorkflowScheduler())
    monkeypatch.setattr(main_module, "metrics_alert_policy_store", policy_store)
    monkeypatch.setattr(
        main_module,
        "workflow_engine",
        WorkflowEngine(
            scheduler=main_module.workflow_scheduler,
            action_executor=main_module.action_layer.execute,
        ),
    )
    store.reset()
    yield
    store.reset()
