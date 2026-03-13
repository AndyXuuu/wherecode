import time

from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app
from control_center.models import ActionExecuteResponse


client = TestClient(app)
FINAL_STATUSES = {"success", "failed", "canceled"}


class StubOrchestratePolicyActionLayer:
    async def execute(self, request):
        lowered = request.text.lower()
        if "role: chief-architect" in lowered:
            return ActionExecuteResponse(
                status="success",
                summary="decomposition generated",
                agent="chief-agent",
                trace_id="act_cmd_orch_chief",
                metadata={
                    "modules": ["news-crawler", "sentiment-analysis"],
                    "decomposition": {
                        "requirement_module_map": {
                            "crawl": ["news-crawler"],
                            "sentiment": ["sentiment-analysis"],
                        },
                        "module_task_packages": {
                            "news-crawler": [
                                {"role": "module-dev", "objective": "implement crawler"},
                                {"role": "doc-manager", "objective": "write crawler docs"},
                                {"role": "qa-test", "objective": "add crawler tests"},
                                {"role": "security-review", "objective": "review crawler security"},
                            ],
                            "sentiment-analysis": [
                                {"role": "module-dev", "objective": "implement sentiment parser"},
                                {"role": "doc-manager", "objective": "write sentiment docs"},
                                {"role": "qa-test", "objective": "add sentiment tests"},
                                {"role": "security-review", "objective": "review parser security"},
                            ],
                        },
                    },
                },
            )
        return ActionExecuteResponse(
            status="success",
            summary="mock execution completed",
            agent=request.agent or "coding-agent",
            trace_id="act_cmd_orch_default",
        )


def wait_for_terminal(command_id: str, timeout: float = 3.0) -> dict:
    deadline = time.time() + timeout
    payload: dict = {}
    while time.time() < deadline:
        response = client.get(f"/commands/{command_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in FINAL_STATUSES:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"command {command_id} did not reach terminal state: {payload}")


def test_create_project_contract_fields() -> None:
    response = client.post(
        "/projects",
        json={
            "name": "contract-project",
            "description": "contract-check",
            "owner": "qa",
            "tags": ["contract", "v1"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    assert payload["id"].startswith("proj_")
    assert payload["name"] == "contract-project"
    assert payload["status"] == "active"
    assert payload["task_count"] == 0
    assert payload["active_task_count"] == 0
    assert payload["owner"] == "qa"
    assert payload["tags"] == ["contract", "v1"]


def test_task_command_snapshot_contract() -> None:
    project = client.post("/projects", json={"name": "snapshot-contract"}).json()
    project_id = project["id"]

    task_resp = client.post(
        f"/projects/{project_id}/tasks",
        json={
            "title": "snapshot-task",
            "description": "task desc",
            "priority": 4,
            "assignee_agent": "coding-agent",
        },
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    task_id = task["id"]
    assert task["project_id"] == project_id
    assert task["assignee_agent"] == "coding-agent"

    cmd_resp = client.post(
        f"/tasks/{task_id}/commands",
        json={
            "text": "run contract check",
            "source": "user",
            "requested_by": "qa",
            "requires_approval": False,
        },
    )
    assert cmd_resp.status_code == 202
    accepted = cmd_resp.json()
    assert accepted["task_id"] == task_id
    assert accepted["project_id"] == project_id
    assert accepted["status"] == "queued"
    assert accepted["poll_url"] == f"/commands/{accepted['command_id']}"

    terminal = wait_for_terminal(accepted["command_id"])
    assert terminal["id"] == accepted["command_id"]
    assert terminal["project_id"] == project_id
    assert terminal["task_id"] == task_id
    assert terminal["executor_agent"] == "coding-agent"
    assert terminal["trace_id"].startswith("act_")

    listed_tasks = client.get(f"/projects/{project_id}/tasks")
    assert listed_tasks.status_code == 200
    tasks = listed_tasks.json()
    assert any(item["id"] == task_id for item in tasks)

    listed_commands = client.get(f"/tasks/{task_id}/commands")
    assert listed_commands.status_code == 200
    commands = listed_commands.json()
    assert any(item["id"] == accepted["command_id"] for item in commands)

    snapshot_resp = client.get(f"/projects/{project_id}/snapshot")
    assert snapshot_resp.status_code == 200
    snapshot = snapshot_resp.json()
    assert snapshot["id"] == project_id
    assert any(item["id"] == task_id for item in snapshot["tasks"])
    snapshot_task = next(item for item in snapshot["tasks"] if item["id"] == task_id)
    assert any(item["id"] == accepted["command_id"] for item in snapshot_task["commands"])


def test_task_default_assignee_agent_is_applied() -> None:
    project = client.post("/projects", json={"name": "default-assignee"}).json()
    response = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "task-with-default-assignee"},
    )
    assert response.status_code == 201
    task = response.json()
    assert task["assignee_agent"] == "auto-agent"


def test_failed_command_contract_and_task_status() -> None:
    project = client.post("/projects", json={"name": "failed-contract"}).json()
    project_id = project["id"]
    task = client.post(f"/projects/{project_id}/tasks", json={"title": "failed-task"}).json()
    task_id = task["id"]

    accepted = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "please fail this command"},
    ).json()
    terminal = wait_for_terminal(accepted["command_id"])

    assert terminal["status"] == "failed"
    assert terminal["error_message"] == "mock execution failed by command content"
    assert terminal["executor_agent"] == "coding-agent"
    assert terminal["trace_id"].startswith("act_")

    task_detail = client.get(f"/tasks/{task_id}")
    assert task_detail.status_code == 200
    task_payload = task_detail.json()
    assert task_payload["status"] == "failed"
    assert task_payload["failed_count"] >= 1

    projects = client.get("/projects").json()
    project_payload = next(item for item in projects if item["id"] == project_id)
    assert project_payload["active_task_count"] == 0


def test_auto_agent_routes_test_commands_to_test_agent() -> None:
    project = client.post("/projects", json={"name": "auto-route-project"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "auto-route-task"},
    ).json()
    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "run pytest for login module"},
    ).json()
    terminal = wait_for_terminal(accepted["command_id"])
    assert terminal["executor_agent"] == "test-agent"
    assert terminal["metadata"]["routing_reason"] == "keyword_rule"
    assert terminal["metadata"]["routing_keyword"] == "pytest"
    assert terminal["metadata"]["routing_rule_id"] == "rule_test_keywords"


def test_command_orchestrate_policy_triggers_workflow_run(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubOrchestratePolicyActionLayer())

    project = client.post("/projects", json={"name": "cmd-orchestrate-policy"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "cmd-orchestrate-task"},
    ).json()

    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={
            "text": (
                "/orchestrate build crawl and sentiment pipeline "
                "--module-hints=crawl,sentiment --max-modules=4 --execute=false"
            ),
            "requested_by": "owner",
        },
    ).json()
    terminal = wait_for_terminal(accepted["command_id"])
    assert terminal["status"] == "success"
    assert terminal["executor_agent"] == "chief-architect"
    assert terminal["metadata"]["command_execution_mode"] == "orchestrate_policy"
    assert terminal["metadata"]["orchestration_status"] == "prepared"
    workflow_state = terminal["metadata"]["workflow_state_latest"]
    assert workflow_state["orchestration_status"] == "prepared"
    assert workflow_state["workflow_run_id"].startswith("wfr_")
    assert "primary_recovery_action" in workflow_state
    workflow_run_id = terminal["metadata"]["workflow_run_id"]
    assert workflow_run_id.startswith("wfr_")

    run_response = client.get(f"/v3/workflows/runs/{workflow_run_id}")
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["task_id"] == task["id"]
    assert run_payload["project_id"] == project["id"]
    assert run_payload["metadata"]["task_workflow_state_latest"]["workflow_run_id"] == workflow_run_id

    task_detail = client.get(f"/tasks/{task['id']}")
    assert task_detail.status_code == 200
    task_metadata = task_detail.json()["metadata"]
    assert task_metadata["workflow_run_id_latest"] == workflow_run_id
    assert task_metadata["workflow_state_latest"]["workflow_run_id"] == workflow_run_id
    assert task_metadata["workflow_state_latest"]["orchestration_status"] == "prepared"


def test_command_orchestrate_policy_blocks_when_requirements_missing() -> None:
    project = client.post("/projects", json={"name": "cmd-orchestrate-blocked"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "cmd-orchestrate-missing-requirements"},
    ).json()

    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "/orchestrate --execute=false"},
    ).json()
    terminal = wait_for_terminal(accepted["command_id"])
    assert terminal["status"] == "failed"
    assert terminal["executor_agent"] == "chief-architect"
    assert "orchestrate status=blocked" in (terminal["error_message"] or "")
    assert "requirements" in (terminal["error_message"] or "")
    workflow_state = terminal["metadata"]["workflow_state_latest"]
    assert workflow_state["orchestration_status"] == "blocked"
    assert workflow_state["primary_recovery_action"] == "retry_with_decompose_payload"
    assert workflow_state["workflow_run_id"].startswith("wfr_")


def test_command_orchestrate_policy_requires_clarification_for_ambiguous_requirements() -> None:
    project = client.post("/projects", json={"name": "cmd-orchestrate-clarification"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "cmd-orchestrate-clarification-task"},
    ).json()

    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={
            "text": (
                "/orchestrate implement tbd crawler and todo rules "
                "--module-hints=crawl --execute=false"
            ),
        },
    ).json()
    terminal = wait_for_terminal(accepted["command_id"])
    assert terminal["status"] == "failed"
    assert "clarification required before orchestrate" in (terminal["error_message"] or "")
    assert terminal["metadata"]["orchestration_status"] == "needs_clarification"
    assert terminal["metadata"]["clarification_required"] is True
    assert "tbd" in terminal["metadata"]["clarification_markers"]


def test_command_orchestrate_latest_and_recover_contract(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubOrchestratePolicyActionLayer())

    project = client.post("/projects", json={"name": "cmd-orchestrate-latest-recover"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "cmd-orchestrate-latest-recover-task"},
    ).json()

    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={
            "text": (
                "/orchestrate build crawl and sentiment pipeline "
                "--module-hints=crawl,sentiment --max-modules=4 --execute=false"
            ),
            "requested_by": "owner",
        },
    ).json()
    terminal = wait_for_terminal(accepted["command_id"])
    assert terminal["status"] == "success"

    workflow_run_id = terminal["metadata"]["workflow_run_id"]
    latest = client.get(f"/v3/workflows/runs/{workflow_run_id}/orchestrate/latest")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload["found"] is True
    record = latest_payload["record"]
    assert record["run_id"] == workflow_run_id
    assert record["orchestration_status"] == "prepared"
    assert record["telemetry_snapshot"]["action_count"] >= 1
    assert "primary_recovery_action" in record["decision_report"]["machine"]

    recover = client.post(
        f"/v3/workflows/runs/{workflow_run_id}/orchestrate/recover",
        json={
            "action": "reconfirm_decomposition",
            "confirmed_by": "owner",
        },
    )
    assert recover.status_code == 200
    recover_payload = recover.json()
    assert recover_payload["selected_action"] == "reconfirm_decomposition"
    assert recover_payload["action_status"] == "executed"
    assert recover_payload["confirmation"] is not None
    assert recover_payload["confirmation"]["confirmation_status"] == "approved"


def test_command_orchestrate_policy_restart_latest_canceled(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubOrchestratePolicyActionLayer())

    project = client.post("/projects", json={"name": "cmd-orch-restart-latest"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "cmd-orch-restart-latest-task"},
    ).json()

    first = client.post(
        f"/tasks/{task['id']}/commands",
        json={
            "text": (
                "/orchestrate build crawl and sentiment pipeline "
                "--module-hints=crawl,sentiment --max-modules=4 --execute=false"
            ),
            "requested_by": "owner",
        },
    ).json()
    first_terminal = wait_for_terminal(first["command_id"])
    assert first_terminal["status"] == "success"
    first_run_id = first_terminal["metadata"]["workflow_run_id"]

    interrupt = client.post(
        f"/v3/workflows/runs/{first_run_id}/interrupt",
        json={"requested_by": "owner", "reason": "manual stop before restart"},
    )
    assert interrupt.status_code == 200
    assert interrupt.json()["run_status"] == "canceled"

    second = client.post(
        f"/tasks/{task['id']}/commands",
        json={
            "text": "/orchestrate --restart-latest-canceled=true --execute=false",
            "requested_by": "owner",
        },
    ).json()
    second_terminal = wait_for_terminal(second["command_id"])
    assert second_terminal["status"] == "success"
    assert second_terminal["metadata"]["orchestration_status"] in {"noop", "prepared"}
    second_run_id = second_terminal["metadata"]["workflow_run_id"]
    assert second_run_id.startswith("wfr_")
    assert second_run_id != first_run_id
    assert (
        second_terminal["metadata"]["orchestration_restart_source_run_id"]
        == first_run_id
    )

    state = second_terminal["metadata"]["workflow_state_latest"]
    assert state["workflow_run_id"] == second_run_id
    assert state["restart_source_run_id"] == first_run_id
    assert state["restart_applied"] is True

    second_run = client.get(f"/v3/workflows/runs/{second_run_id}")
    assert second_run.status_code == 200
    second_run_payload = second_run.json()
    assert second_run_payload["metadata"]["restart"]["source_run_id"] == first_run_id

    task_detail = client.get(f"/tasks/{task['id']}")
    assert task_detail.status_code == 200
    task_metadata = task_detail.json()["metadata"]
    assert task_metadata["workflow_run_id_latest"] == second_run_id
    assert task_metadata["workflow_run_restart_source"] == first_run_id
    assert task_metadata["workflow_run_restart_applied"] is True


def test_command_orchestrate_policy_auto_restart_when_no_requirements(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", StubOrchestratePolicyActionLayer())
    original_policy = main_module.command_orchestration_policy_service._restart_canceled_policy
    main_module.command_orchestration_policy_service._restart_canceled_policy = (
        "auto_if_no_requirements"
    )
    try:
        project = client.post(
            "/projects", json={"name": "cmd-orch-auto-restart-canceled"}
        ).json()
        task = client.post(
            f"/projects/{project['id']}/tasks",
            json={"title": "cmd-orch-auto-restart-canceled-task"},
        ).json()

        first = client.post(
            f"/tasks/{task['id']}/commands",
            json={
                "text": (
                    "/orchestrate build crawl and sentiment pipeline "
                    "--module-hints=crawl,sentiment --max-modules=4 --execute=false"
                ),
                "requested_by": "owner",
            },
        ).json()
        first_terminal = wait_for_terminal(first["command_id"])
        assert first_terminal["status"] == "success"
        first_run_id = first_terminal["metadata"]["workflow_run_id"]

        interrupt = client.post(
            f"/v3/workflows/runs/{first_run_id}/interrupt",
            json={"requested_by": "owner", "reason": "manual stop before auto restart"},
        )
        assert interrupt.status_code == 200
        assert interrupt.json()["run_status"] == "canceled"

        second = client.post(
            f"/tasks/{task['id']}/commands",
            json={
                "text": "/orchestrate --execute=false",
                "requested_by": "owner",
            },
        ).json()
        second_terminal = wait_for_terminal(second["command_id"])
        assert second_terminal["status"] == "success"
        second_run_id = second_terminal["metadata"]["workflow_run_id"]
        assert second_run_id != first_run_id
        assert (
            second_terminal["metadata"]["orchestration_restart_source_run_id"]
            == first_run_id
        )
        assert second_terminal["metadata"]["orchestration_restart_mode"] == (
            "auto_if_no_requirements"
        )
        assert second_terminal["metadata"]["orchestration_restart_requested"] is True

        workflow_state = second_terminal["metadata"]["workflow_state_latest"]
        assert workflow_state["restart_source_run_id"] == first_run_id
        assert workflow_state["restart_applied"] is True
        assert workflow_state["restart_mode"] == "auto_if_no_requirements"
        assert workflow_state["restart_requested"] is True
    finally:
        main_module.command_orchestration_policy_service._restart_canceled_policy = (
            original_policy
        )


def test_approval_contract_status_transition() -> None:
    project = client.post("/projects", json={"name": "approval-contract"}).json()
    project_id = project["id"]
    task = client.post(f"/projects/{project_id}/tasks", json={"title": "approval-task"}).json()
    task_id = task["id"]

    accepted = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "deploy staging", "requires_approval": True},
    ).json()
    command_id = accepted["command_id"]
    assert accepted["status"] == "waiting_approval"

    waiting = client.get(f"/commands/{command_id}")
    assert waiting.status_code == 200
    assert waiting.json()["status"] == "waiting_approval"

    approved = client.post(
        f"/commands/{command_id}/approve",
        json={"approved_by": "owner"},
    )
    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["approved_by"] == "owner"
    assert approved_payload["status"] == "queued"

    terminal = wait_for_terminal(command_id)
    assert terminal["status"] in {"success", "failed"}


def test_reload_agent_routing_contract() -> None:
    response = client.post("/agent-routing/reload")
    assert response.status_code == 200
    payload = response.json()
    assert payload["default_agent"] == "coding-agent"
    assert isinstance(payload["rules"], list)
    assert len(payload["rules"]) >= 1
    first_rule = payload["rules"][0]
    assert {"id", "agent", "priority", "enabled", "keywords"}.issubset(first_rule.keys())


def test_command_orchestrate_policy_config_contract() -> None:
    response = client.get("/config/command-orchestrate-policy")
    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload
    assert "prefixes" in payload
    assert "default_max_modules" in payload
    assert "default_strategy" in payload
    assert "restart_canceled_policy" in payload
    assert isinstance(payload["prefixes"], list)
    assert payload["restart_canceled_policy"] in {
        "off",
        "auto_if_no_requirements",
        "always",
    }


def test_v3_run_report_contract() -> None:
    run = client.post(
        "/v3/workflows/runs",
        json={"project_id": "proj_contract_report", "requested_by": "owner"},
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

    response = client.get(f"/v3/runs/{run_id}/report")
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert "run_status" in payload
    assert "current_stage" in payload
    assert "requirement_status" in payload
    assert "clarification_rounds" in payload
    assert "assumption_used" in payload
    assert "blocked_reason" in payload
    assert "next_action_hint" in payload
    assert "accepted" in payload
    assert "acceptance_evidence_complete" in payload
    assert isinstance(payload["workitem_status_counts"], dict)
    assert isinstance(payload["gate_status_counts"], dict)
    assert isinstance(payload["artifact_type_counts"], dict)


def test_get_and_update_agent_routing_contract() -> None:
    original = client.get("/agent-routing")
    assert original.status_code == 200
    original_payload = original.json()

    update_payload = {
        "default_agent": "coding-agent",
        "rules": [
            {
                "id": "rule_review_only",
                "agent": "review-agent",
                "priority": 1,
                "enabled": True,
                "keywords": ["review"],
            }
        ],
    }

    try:
        updated = client.put("/agent-routing", json=update_payload)
        assert updated.status_code == 200
        assert updated.json()["rules"][0]["id"] == "rule_review_only"

        project = client.post("/projects", json={"name": "routing-update-project"}).json()
        task = client.post(
            f"/projects/{project['id']}/tasks",
            json={"title": "routing-update-task"},
        ).json()
        accepted = client.post(
            f"/tasks/{task['id']}/commands",
            json={"text": "please review this module"},
        ).json()
        terminal = wait_for_terminal(accepted["command_id"])
        assert terminal["executor_agent"] == "review-agent"
        assert terminal["metadata"]["routing_rule_id"] == "rule_review_only"
    finally:
        restore = client.put("/agent-routing", json=original_payload)
        assert restore.status_code == 200
