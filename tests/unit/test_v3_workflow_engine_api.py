from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app
from control_center.models import ActionExecuteResponse


client = TestClient(app)


class StubChiefArchitectActionLayer:
    def __init__(self, response: ActionExecuteResponse) -> None:
        self.response = response
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        return self.response


def test_v3_workflow_engine_bootstrap_and_execute_success() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_flow_success", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth", "billing"]},
    )
    assert bootstrap.status_code == 200
    assert len(bootstrap.json()) == 11

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run_status"] == "succeeded"
    assert payload["failed_count"] == 0
    assert payload["remaining_pending_count"] == 0

    run_after = client.get(f"/v3/workflows/runs/{run_id}")
    assert run_after.status_code == 200
    assert run_after.json()["status"] == "succeeded"

    gates = client.get(f"/v3/workflows/runs/{run_id}/gates")
    assert gates.status_code == 200
    assert len(gates.json()) >= 1

    artifacts = client.get(f"/v3/workflows/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    artifact_types = {item["artifact_type"] for item in artifacts.json()}
    assert "acceptance_report" in artifact_types
    assert "release_note" in artifact_types
    assert "rollback_plan" in artifact_types


def test_v3_workflow_engine_execute_failure_path() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_flow_fail", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth", "fail-module"]},
    )
    assert bootstrap.status_code == 200

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run_status"] == "failed"
    assert payload["failed_count"] >= 1


def test_v3_workflow_execute_requires_confirmed_requirement() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_req_gate", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    response = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 5},
    )
    assert response.status_code == 409
    assert "requirement is not confirmed" in response.json()["detail"]


def test_v3_run_visibility_api_contract() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_visibility_api", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert bootstrap.status_code == 200

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert execute.status_code == 200

    timeline = client.get(f"/v3/runs/{run_id}/timeline")
    assert timeline.status_code == 200
    timeline_payload = timeline.json()
    assert timeline_payload["run_id"] == run_id
    assert "current_stage" in timeline_payload
    assert "requirement_status" in timeline_payload
    assert "blocked_reason" in timeline_payload
    assert "next_action_hint" in timeline_payload
    assert isinstance(timeline_payload["events"], list)

    artifacts = client.get(f"/v3/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    artifacts_payload = artifacts.json()
    assert artifacts_payload["run_id"] == run_id
    assert "acceptance_evidence_complete" in artifacts_payload
    assert isinstance(artifacts_payload["artifacts"], list)

    report = client.get(f"/v3/runs/{run_id}/report")
    assert report.status_code == 200
    report_payload = report.json()
    assert report_payload["run_id"] == run_id
    assert "workitem_status_counts" in report_payload
    assert "gate_status_counts" in report_payload
    assert "artifact_type_counts" in report_payload


def test_v3_workflow_engine_rejects_duplicate_bootstrap() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_dup", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    first = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert first.status_code == 200

    second = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["billing"]},
    )
    assert second.status_code == 422


def test_v3_workflow_engine_gate_reflow_success_path() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_gate_reflow", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["doc-reflow-once"]},
    )
    assert bootstrap.status_code == 200

    execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 50},
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["run_status"] == "succeeded"

    gates = client.get(f"/v3/workflows/runs/{run_id}/gates")
    assert gates.status_code == 200
    gate_statuses = {item["status"] for item in gates.json()}
    assert "failed" in gate_statuses
    assert "passed" in gate_statuses


def test_v3_workflow_engine_discussion_flow_resume() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_discussion", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["needs-discussion"]},
    )
    assert bootstrap.status_code == 200

    first_execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert first_execute.status_code == 200
    first_payload = first_execute.json()
    assert first_payload["run_status"] == "blocked"
    assert first_payload["waiting_discussion_count"] >= 1
    assert len(first_payload["waiting_discussion_workitem_ids"]) >= 1

    target_workitem_id = first_payload["waiting_discussion_workitem_ids"][0]
    discussions = client.get(f"/v3/workflows/workitems/{target_workitem_id}/discussions")
    assert discussions.status_code == 200
    discussion_list = discussions.json()
    assert len(discussion_list) >= 1
    assert discussion_list[-1]["status"] == "open"

    resolve = client.post(
        f"/v3/workflows/workitems/{target_workitem_id}/discussion/resolve",
        json={"decision": "use option-a", "resolved_by": "chief-architect"},
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"

    second_execute = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 30},
    )
    assert second_execute.status_code == 200
    second_payload = second_execute.json()
    assert second_payload["run_status"] == "succeeded"


def test_v3_workflow_engine_release_approval_switch() -> None:
    main_module.workflow_engine._release_requires_approval = True
    try:
        run = client.post(
            "/v3/workflows/runs",
            json={"project_id": "proj_release_approval", "requested_by": "andy"},
        ).json()
        run_id = run["id"]

        bootstrap = client.post(
            f"/v3/workflows/runs/{run_id}/bootstrap",
            json={"modules": ["auth"]},
        )
        assert bootstrap.status_code == 200

        first_execute = client.post(
            f"/v3/workflows/runs/{run_id}/execute",
            json={"max_loops": 30},
        )
        assert first_execute.status_code == 200
        payload = first_execute.json()
        assert payload["run_status"] == "waiting_approval"
        assert payload["waiting_approval_count"] == 1
        target = payload["waiting_approval_workitem_ids"][0]

        approve = client.post(
            f"/v3/workflows/workitems/{target}/approve",
            json={"approved_by": "owner"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "ready"

        second_execute = client.post(
            f"/v3/workflows/runs/{run_id}/execute",
            json={"max_loops": 30},
        )
        assert second_execute.status_code == 200
        assert second_execute.json()["run_status"] == "succeeded"
    finally:
        main_module.workflow_engine._release_requires_approval = False


def test_v3_workflow_run_interrupt_cancels_execution() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_interrupt_api", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert bootstrap.status_code == 200

    interrupt = client.post(
        f"/v3/workflows/runs/{run_id}/interrupt",
        json={
            "requested_by": "owner",
            "reason": "manual stop for reprioritization",
            "skip_non_terminal_workitems": True,
        },
    )
    assert interrupt.status_code == 200
    interrupt_payload = interrupt.json()
    assert interrupt_payload["previous_status"] == "running"
    assert interrupt_payload["run_status"] == "canceled"
    assert interrupt_payload["interrupt_applied"] is True
    assert len(interrupt_payload["skipped_workitem_ids"]) >= 1

    run_after_interrupt = client.get(f"/v3/workflows/runs/{run_id}")
    assert run_after_interrupt.status_code == 200
    assert run_after_interrupt.json()["status"] == "canceled"

    execute_after_interrupt = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 20},
    )
    assert execute_after_interrupt.status_code == 200
    execute_payload = execute_after_interrupt.json()
    assert execute_payload["run_status"] == "canceled"
    assert execute_payload["executed_count"] == 0
    assert execute_payload["failed_count"] == 0

    interrupt_again = client.post(
        f"/v3/workflows/runs/{run_id}/interrupt",
        json={"reason": "second stop"},
    )
    assert interrupt_again.status_code == 200
    assert interrupt_again.json()["interrupt_applied"] is False
    assert interrupt_again.json()["run_status"] == "canceled"


def test_v3_workflow_run_restart_after_interrupt() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_restart_api", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert bootstrap.status_code == 200

    interrupt = client.post(
        f"/v3/workflows/runs/{run_id}/interrupt",
        json={"requested_by": "owner", "reason": "stop for restart"},
    )
    assert interrupt.status_code == 200
    assert interrupt.json()["run_status"] == "canceled"

    restart = client.post(
        f"/v3/workflows/runs/{run_id}/restart",
        json={"requested_by": "owner", "reason": "continue", "copy_decomposition": True},
    )
    assert restart.status_code == 200
    restart_payload = restart.json()
    assert restart_payload["source_run_id"] == run_id
    restarted_run_id = restart_payload["restarted_run_id"]
    assert restarted_run_id.startswith("wfr_")
    assert restarted_run_id != run_id
    assert restart_payload["restarted_run_status"] == "running"

    restarted_run = client.get(f"/v3/workflows/runs/{restarted_run_id}")
    assert restarted_run.status_code == 200
    assert restarted_run.json()["status"] == "running"
    assert restarted_run.json()["metadata"]["restart"]["source_run_id"] == run_id


def test_v3_orchestrate_recover_restarts_canceled_run() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_orch_restart", "requested_by": "andy"},
    ).json()
    run_id = run["id"]

    bootstrap = client.post(
        f"/v3/workflows/runs/{run_id}/bootstrap",
        json={"modules": ["auth"]},
    )
    assert bootstrap.status_code == 200
    interrupt = client.post(
        f"/v3/workflows/runs/{run_id}/interrupt",
        json={"requested_by": "owner", "reason": "manual stop"},
    )
    assert interrupt.status_code == 200

    orchestrate = client.post(
        f"/v3/workflows/runs/{run_id}/orchestrate",
        json={"strategy": "balanced", "execute": True},
    )
    assert orchestrate.status_code == 200
    orchestrate_payload = orchestrate.json()
    assert orchestrate_payload["orchestration_status"] == "blocked"
    assert "workflow run is canceled" in (orchestrate_payload["reason"] or "")
    machine = orchestrate_payload["decision_report"]["machine"]
    assert machine["primary_recovery_action"] == "restart_workflow_run"

    recover = client.post(
        f"/v3/workflows/runs/{run_id}/orchestrate/recover",
        json={"requested_by": "owner"},
    )
    assert recover.status_code == 200
    recover_payload = recover.json()
    assert recover_payload["selected_action"] == "restart_workflow_run"
    assert recover_payload["action_status"] == "executed"
    restarted_run_id = recover_payload["restarted_run_id"]
    assert isinstance(restarted_run_id, str)
    assert restarted_run_id.startswith("wfr_")
    assert recover_payload["restarted_run_status"] == "running"

    restarted_run = client.get(f"/v3/workflows/runs/{restarted_run_id}")
    assert restarted_run.status_code == 200
    assert restarted_run.json()["metadata"]["restart"]["source_run_id"] == run_id


def test_v3_workflow_decompose_bootstrap_success(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_success", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into market-data, sentiment-crawl",
            agent="chief-agent",
            trace_id="act_decompose_001",
            metadata={
                "modules": ["market-data", "sentiment-crawl"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["market-data"],
                        "sentiment": ["sentiment-crawl"],
                    },
                    "module_task_packages": {
                        "market-data": [
                            {"role": "module-dev", "objective": "implement data ingestion"},
                            {"role": "doc-manager", "objective": "write module docs"},
                            {"role": "qa-test", "objective": "add module tests"},
                            {"role": "security-review", "objective": "run security checks"},
                        ],
                        "sentiment-crawl": [
                            {"role": "module-dev", "objective": "implement sentiment parser"},
                            {"role": "doc-manager", "objective": "document sentiment flow"},
                            {"role": "qa-test", "objective": "verify sentiment quality"},
                            {"role": "security-review", "objective": "review parser safety"},
                        ],
                    },
                    "modules": [
                        {
                            "module_key": "market-data",
                            "coverage_tags": ["crawl"],
                        },
                        {
                            "module_key": "sentiment-crawl",
                            "coverage_tags": ["sentiment"],
                        },
                    ],
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build market sentiment pipeline with crawl and analysis",
            "max_modules": 6,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["modules"] == ["market-data", "sentiment-crawl"]
    assert payload["chief_agent"] == "chief-agent"
    assert payload["workitems"] == []
    assert payload["confirmation_required"] is True
    assert payload["confirmation_status"] == "pending"
    assert isinstance(payload["confirmation_token"], str)

    assert len(stub_action_layer.calls) == 1
    chief_request = stub_action_layer.calls[0]
    assert chief_request.role == "chief-architect"
    assert chief_request.project_id == "proj_decompose_success"
    assert chief_request.module_key == "workflow_decomposition"
    assert "software development project module decomposition" in chief_request.text

    run_after = client.get(f"/v3/workflows/runs/{run_id}")
    assert run_after.status_code == 200
    chief_metadata = run_after.json()["metadata"]["chief_decomposition"]
    assert chief_metadata["modules"] == ["market-data", "sentiment-crawl"]
    assert chief_metadata["required_coverage_tags"] == ["crawl", "sentiment"]
    assert chief_metadata["missing_coverage_tags"] == []
    assert chief_metadata["requirement_module_map"] == {
        "crawl": ["market-data"],
        "sentiment": ["sentiment-crawl"],
    }
    assert chief_metadata["missing_mapping_tags"] == []
    assert chief_metadata["invalid_mapping_modules"] == {}
    assert chief_metadata["mapping_explicit"] is True
    assert chief_metadata["task_package_explicit"] is True
    assert chief_metadata["missing_task_package_modules"] == []
    assert chief_metadata["invalid_task_package_roles"] == {}
    assert chief_metadata["missing_task_package_roles"] == {}
    assert "module_routing_decisions" in chief_metadata
    routing_market = chief_metadata["module_routing_decisions"]["market-data"]
    assert routing_market["target"]["role"] == "module-dev"
    assert routing_market["target"]["capability_id"] == "builtin.skill.data-pipeline"
    assert routing_market["target"]["executor"] == "coding-agent"
    assert chief_metadata["confirmation"]["status"] == "pending"

    routing_pending = client.get(
        f"/v3/workflows/runs/{run_id}/routing-decisions",
    )
    assert routing_pending.status_code == 200
    routing_pending_payload = routing_pending.json()
    assert routing_pending_payload["run_id"] == run_id
    assert routing_pending_payload["source"] == "pending"
    assert routing_pending_payload["has_routing_decisions"] is True
    assert routing_pending_payload["module_count"] == 2
    routing_pending_modules = {
        item["module_key"]: item for item in routing_pending_payload["decisions"]
    }
    assert routing_pending_modules["market-data"]["rule_id"] == "data-pipeline-python"
    assert routing_pending_modules["market-data"]["capability_id"] == "builtin.skill.data-pipeline"
    assert routing_pending_modules["market-data"]["executor"] == "coding-agent"
    assert routing_pending_modules["market-data"]["required_checks"] == [
        "backend-quick",
        "projects",
    ]

    execute_before_confirm = client.post(
        f"/v3/workflows/runs/{run_id}/execute",
        json={"max_loops": 10},
    )
    assert execute_before_confirm.status_code == 409
    assert execute_before_confirm.json()["detail"].startswith(
        "decomposition confirmation required before execute"
    )

    confirm = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
        json={
            "confirmed_by": "owner",
            "approved": True,
            "expected_modules": ["market-data", "sentiment-crawl"],
            "confirmation_token": payload["confirmation_token"],
        },
    )
    assert confirm.status_code == 200
    confirm_payload = confirm.json()
    assert confirm_payload["approved"] is True
    assert confirm_payload["confirmation_status"] == "approved"
    assert confirm_payload["modules"] == ["market-data", "sentiment-crawl"]
    assert len(confirm_payload["workitems"]) == 11
    module_dev_items = [
        item
        for item in confirm_payload["workitems"]
        if item["module_key"] == "market-data" and item["role"] == "module-dev"
    ]
    assert len(module_dev_items) == 1
    module_dev_meta = module_dev_items[0]["metadata"]
    assert module_dev_meta["task_routing_capability_id"] == "builtin.skill.data-pipeline"
    assert module_dev_meta["task_routing_executor"] == "coding-agent"
    assert module_dev_meta["task_routing_rule_id"] == "data-pipeline-python"

    qa_items = [
        item
        for item in confirm_payload["workitems"]
        if item["module_key"] == "market-data" and item["role"] == "qa-test"
    ]
    assert len(qa_items) == 1
    qa_meta = qa_items[0]["metadata"]
    assert qa_meta["task_routing_required_checks"] == ["backend-quick", "projects"]

    routing_after_confirm = client.get(
        f"/v3/workflows/runs/{run_id}/routing-decisions",
    )
    assert routing_after_confirm.status_code == 200
    routing_after_confirm_payload = routing_after_confirm.json()
    assert routing_after_confirm_payload["source"] == "chief"
    assert routing_after_confirm_payload["confirmation_status"] == "approved"


def test_v3_workflow_decompose_bootstrap_pending_query_lifecycle(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_pending_lifecycle", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    pending_before = client.get(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/pending",
    )
    assert pending_before.status_code == 200
    assert pending_before.json()["has_pending_confirmation"] is False
    assert pending_before.json()["confirmation_status"] is None

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into market-data, sentiment-crawl",
            agent="chief-agent",
            trace_id="act_decompose_011",
            metadata={
                "modules": ["market-data", "sentiment-crawl"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["market-data"],
                        "sentiment": ["sentiment-crawl"],
                    },
                    "module_task_packages": {
                        "market-data": [
                            {"role": "module-dev", "objective": "implement data ingestion"},
                            {"role": "doc-manager", "objective": "write module docs"},
                            {"role": "qa-test", "objective": "add module tests"},
                            {"role": "security-review", "objective": "run security checks"},
                        ],
                        "sentiment-crawl": [
                            {"role": "module-dev", "objective": "implement sentiment parser"},
                            {"role": "doc-manager", "objective": "document sentiment flow"},
                            {"role": "qa-test", "objective": "verify sentiment quality"},
                            {"role": "security-review", "objective": "review parser safety"},
                        ],
                    },
                    "modules": [
                        {
                            "module_key": "market-data",
                            "coverage_tags": ["crawl"],
                        },
                        {
                            "module_key": "sentiment-crawl",
                            "coverage_tags": ["sentiment"],
                        },
                    ],
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    decompose = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build market sentiment pipeline with crawl and analysis",
            "max_modules": 6,
            "module_hints": ["crawl", "sentiment"],
        },
    )
    assert decompose.status_code == 200
    token = decompose.json()["confirmation_token"]

    pending_after_decompose = client.get(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/pending",
    )
    assert pending_after_decompose.status_code == 200
    pending_payload = pending_after_decompose.json()
    assert pending_payload["has_pending_confirmation"] is True
    assert pending_payload["confirmation_status"] == "pending"
    assert pending_payload["confirmation_token"] == token
    assert pending_payload["modules"] == ["market-data", "sentiment-crawl"]
    assert pending_payload["chief_trace_id"] == "act_decompose_011"
    assert pending_payload["module_hints"] == ["crawl", "sentiment"]

    confirm = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
        json={
            "confirmed_by": "owner",
            "approved": True,
            "expected_modules": ["market-data", "sentiment-crawl"],
            "confirmation_token": token,
        },
    )
    assert confirm.status_code == 200

    pending_after_approve = client.get(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/pending",
    )
    assert pending_after_approve.status_code == 200
    pending_after_approve_payload = pending_after_approve.json()
    assert pending_after_approve_payload["has_pending_confirmation"] is False
    assert pending_after_approve_payload["confirmation_status"] is None
    assert pending_after_approve_payload["modules"] == []


def test_v3_workflow_decompose_bootstrap_pending_query_after_reject(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_pending_after_reject", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_012",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["daily-report"],
                    },
                    "module_task_packages": {
                        "news-crawler": [
                            {"role": "module-dev", "objective": "implement crawler"},
                            {"role": "doc-manager", "objective": "document crawler"},
                            {"role": "qa-test", "objective": "test crawler"},
                            {"role": "security-review", "objective": "review crawler"},
                        ],
                        "daily-report": [
                            {"role": "module-dev", "objective": "implement reporter"},
                            {"role": "doc-manager", "objective": "document reporter"},
                            {"role": "qa-test", "objective": "test reporter"},
                            {"role": "security-review", "objective": "review reporter"},
                        ],
                    },
                    "modules": [
                        {
                            "module_key": "news-crawler",
                            "coverage_tags": ["crawl"],
                        },
                        {
                            "module_key": "daily-report",
                            "coverage_tags": ["report"],
                        },
                    ],
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    decompose = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert decompose.status_code == 200
    token = decompose.json()["confirmation_token"]

    reject = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
        json={
            "confirmed_by": "owner",
            "approved": False,
            "reason": "need module redesign",
            "confirmation_token": token,
        },
    )
    assert reject.status_code == 200

    pending_after_reject = client.get(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/pending",
    )
    assert pending_after_reject.status_code == 200
    pending_payload = pending_after_reject.json()
    assert pending_payload["has_pending_confirmation"] is False
    assert pending_payload["confirmation_status"] == "rejected"
    assert pending_payload["confirmation_token"] == token
    assert pending_payload["reason"] == "need module redesign"
    assert pending_payload["modules"] == ["news-crawler", "daily-report"]
    assert pending_payload["confirmed_by"] == "owner"


def test_v3_workflow_decompose_bootstrap_rejects_empty_modules(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK", False)

    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_empty", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="no split available",
            agent="chief-agent",
            trace_id="act_decompose_002",
            metadata={},
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={"requirements": "unknown requirement"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "chief decomposition returned no modules"


def test_v3_workflow_decompose_bootstrap_allows_synthetic_fallback_on_empty_modules(
    monkeypatch,
) -> None:
    monkeypatch.setattr(main_module, "DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK", True)

    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_empty_fallback", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="no split available",
            agent="chief-agent",
            trace_id="act_decompose_002_fallback",
            metadata={},
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["modules"]
    assert payload["confirmation_required"] is True
    assert payload["confirmation_status"] == "pending"
    assert payload["chief_metadata"]["synthetic_fallback"] is True
    assert (
        payload["chief_metadata"]["synthetic_fallback_reason"]
        == "chief decomposition returned no modules"
    )


def test_v3_workflow_decompose_bootstrap_rejects_non_success_status(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK", False)

    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_failed", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="failed",
            summary="provider timeout",
            agent="chief-agent",
            trace_id="act_decompose_003",
            metadata={},
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={"requirements": "market analysis platform v1"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "chief decomposition failed: status=failed"


def test_v3_workflow_decompose_bootstrap_allows_synthetic_fallback_on_non_success(
    monkeypatch,
) -> None:
    monkeypatch.setattr(main_module, "DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK", True)

    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_fallback", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="failed",
            summary="provider timeout",
            agent="chief-agent",
            trace_id="act_decompose_003_fallback",
            metadata={},
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["modules"]
    assert payload["confirmation_required"] is True
    assert payload["confirmation_status"] == "pending"
    assert payload["chief_metadata"]["synthetic_fallback"] is True


def test_v3_workflow_decompose_bootstrap_rejects_missing_coverage_tags(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_missing_coverage", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler only",
            agent="chief-agent",
            trace_id="act_decompose_004",
            metadata={"modules": ["news-crawler"]},
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "chief decomposition missing required coverage tags: report"


def test_v3_workflow_decompose_bootstrap_rejects_missing_requirement_module_map(
    monkeypatch,
) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_missing_map", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_005",
            metadata={"modules": ["news-crawler", "daily-report"]},
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "chief decomposition missing requirement-module mapping"


def test_v3_workflow_decompose_bootstrap_rejects_mapping_unknown_module(
    monkeypatch,
) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_invalid_map", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_006",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["ghost-module"],
                    }
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "chief decomposition requirement-module mapping references unknown modules: "
        "report=>ghost-module"
    )


def test_v3_workflow_decompose_bootstrap_rejects_missing_module_task_packages(
    monkeypatch,
) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_missing_task_packages", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_007",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["daily-report"],
                    }
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "chief decomposition missing module task packages"


def test_v3_workflow_decompose_bootstrap_rejects_missing_required_task_roles(
    monkeypatch,
) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_missing_task_roles", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_008",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["daily-report"],
                    },
                    "module_task_packages": {
                        "news-crawler": [
                            {"role": "module-dev", "objective": "implement crawler"},
                        ],
                        "daily-report": [
                            {"role": "module-dev", "objective": "implement reporter"},
                        ],
                    },
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    response = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "chief decomposition module task packages missing required roles: "
        "daily-report=>doc-manager,qa-test,security-review, "
        "news-crawler=>doc-manager,qa-test,security-review"
    )


def test_v3_workflow_decompose_bootstrap_confirm_reject_path(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_confirm_reject", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_009",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["daily-report"],
                    },
                    "module_task_packages": {
                        "news-crawler": [
                            {"role": "module-dev", "objective": "implement crawler"},
                            {"role": "doc-manager", "objective": "document crawler"},
                            {"role": "qa-test", "objective": "test crawler"},
                            {"role": "security-review", "objective": "review crawler"},
                        ],
                        "daily-report": [
                            {"role": "module-dev", "objective": "implement reporter"},
                            {"role": "doc-manager", "objective": "document reporter"},
                            {"role": "qa-test", "objective": "test reporter"},
                            {"role": "security-review", "objective": "review reporter"},
                        ],
                    },
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    decompose = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert decompose.status_code == 200
    token = decompose.json()["confirmation_token"]

    reject = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
        json={
            "confirmed_by": "owner",
            "approved": False,
            "reason": "modules need refinement",
            "confirmation_token": token,
        },
    )
    assert reject.status_code == 200
    reject_payload = reject.json()
    assert reject_payload["approved"] is False
    assert reject_payload["confirmation_status"] == "rejected"
    assert reject_payload["workitems"] == []


def test_v3_workflow_decompose_bootstrap_confirm_rejects_token_mismatch(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_decompose_confirm_token", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_decompose_010",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["daily-report"],
                    },
                    "module_task_packages": {
                        "news-crawler": [
                            {"role": "module-dev", "objective": "implement crawler"},
                            {"role": "doc-manager", "objective": "document crawler"},
                            {"role": "qa-test", "objective": "test crawler"},
                            {"role": "security-review", "objective": "review crawler"},
                        ],
                        "daily-report": [
                            {"role": "module-dev", "objective": "implement reporter"},
                            {"role": "doc-manager", "objective": "document reporter"},
                            {"role": "qa-test", "objective": "test reporter"},
                            {"role": "security-review", "objective": "review reporter"},
                        ],
                    },
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    decompose = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
        },
    )
    assert decompose.status_code == 200

    confirm = client.post(
        f"/v3/workflows/runs/{run_id}/decompose-bootstrap/confirm",
        json={
            "confirmed_by": "owner",
            "approved": True,
            "confirmation_token": "decomp_wrongtoken",
        },
    )
    assert confirm.status_code == 409
    assert confirm.json()["detail"] == "confirmation token mismatch"


def test_v3_workflow_orchestrate_recover_blocks_without_action_or_latest() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_orch_recover_none", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    recover = client.post(
        f"/v3/workflows/runs/{run_id}/orchestrate/recover",
        json={},
    )
    assert recover.status_code == 200
    payload = recover.json()
    assert payload["action_source"] == "none"
    assert payload["selected_action"] is None
    assert payload["action_status"] == "blocked"
    assert payload["reason"] == "no recovery action in request or latest decision report"


def test_v3_workflow_orchestrate_recover_uses_latest_primary_action(monkeypatch) -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_orch_recover_latest", "requested_by": "owner"},
    ).json()
    run_id = run["id"]

    blocked_orchestrate = client.post(
        f"/v3/workflows/runs/{run_id}/orchestrate",
        json={
            "force_redecompose": True,
            "execute": False,
        },
    )
    assert blocked_orchestrate.status_code == 200
    blocked_payload = blocked_orchestrate.json()
    assert blocked_payload["orchestration_status"] == "blocked"
    assert (
        blocked_payload["decision_report"]["machine"]["primary_recovery_action"]
        == "retry_with_decompose_payload"
    )

    stub_action_layer = StubChiefArchitectActionLayer(
        ActionExecuteResponse(
            status="success",
            summary="split into crawler and reporter",
            agent="chief-agent",
            trace_id="act_orchestrate_recover_001",
            metadata={
                "modules": ["news-crawler", "daily-report"],
                "decomposition": {
                    "requirement_module_map": {
                        "crawl": ["news-crawler"],
                        "report": ["daily-report"],
                    },
                    "module_task_packages": {
                        "news-crawler": [
                            {"role": "module-dev", "objective": "implement crawler"},
                            {"role": "doc-manager", "objective": "document crawler"},
                            {"role": "qa-test", "objective": "test crawler"},
                            {"role": "security-review", "objective": "review crawler"},
                        ],
                        "daily-report": [
                            {"role": "module-dev", "objective": "implement reporter"},
                            {"role": "doc-manager", "objective": "document reporter"},
                            {"role": "qa-test", "objective": "test reporter"},
                            {"role": "security-review", "objective": "review reporter"},
                        ],
                    },
                },
            },
        )
    )
    monkeypatch.setattr(main_module, "action_layer", stub_action_layer)

    recover = client.post(
        f"/v3/workflows/runs/{run_id}/orchestrate/recover",
        json={
            "requirements": "build crawl and daily report pipeline",
            "module_hints": ["crawl", "report"],
            "max_modules": 4,
            "execute": False,
        },
    )
    assert recover.status_code == 200
    payload = recover.json()
    assert payload["action_source"] == "latest_primary"
    assert payload["selected_action"] == "retry_with_decompose_payload"
    assert payload["action_status"] == "executed"
    assert payload["orchestrate"] is not None
    assert payload["orchestrate"]["orchestration_status"] == "prepared"
