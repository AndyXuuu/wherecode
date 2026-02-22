import time

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)
FINAL_STATUSES = {"success", "failed", "canceled"}


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
    assert terminal["executor_agent"] == "coding"
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
    assert terminal["executor_agent"] == "coding"
    assert terminal["trace_id"].startswith("act_")

    task_detail = client.get(f"/tasks/{task_id}")
    assert task_detail.status_code == 200
    task_payload = task_detail.json()
    assert task_payload["status"] == "failed"
    assert task_payload["failed_count"] >= 1

    projects = client.get("/projects").json()
    project_payload = next(item for item in projects if item["id"] == project_id)
    assert project_payload["active_task_count"] == 0


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
