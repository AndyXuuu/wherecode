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
