import time

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)
FINAL_STATUSES = {"success", "failed", "canceled"}


def wait_for_command_terminal_status(command_id: str, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    last_payload: dict = {}
    while time.time() < deadline:
        response = client.get(f"/commands/{command_id}")
        assert response.status_code == 200
        payload = response.json()
        last_payload = payload
        if payload["status"] in FINAL_STATUSES:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"command {command_id} not terminal within timeout, last={last_payload}")


def test_http_async_command_flow() -> None:
    project = client.post("/projects", json={"name": "proj-http-async"}).json()
    project_id = project["id"]

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "task-http-async"},
    ).json()
    task_id = task["id"]

    accepted = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "run unit tests"},
    )
    assert accepted.status_code == 202
    payload = accepted.json()
    command_id = payload["command_id"]
    assert payload["poll_url"] == f"/commands/{command_id}"

    command = wait_for_command_terminal_status(command_id)
    assert command["status"] in FINAL_STATUSES


def test_approval_command_flow() -> None:
    project = client.post("/projects", json={"name": "proj-approval"}).json()
    project_id = project["id"]
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "task-approval"},
    ).json()

    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "deploy to staging", "requires_approval": True},
    )
    assert accepted.status_code == 202
    command_id = accepted.json()["command_id"]

    waiting = client.get(f"/commands/{command_id}").json()
    assert waiting["status"] == "waiting_approval"

    approved = client.post(
        f"/commands/{command_id}/approve",
        json={"approved_by": "owner"},
    )
    assert approved.status_code == 200

    result = wait_for_command_terminal_status(command_id)
    assert result["status"] in FINAL_STATUSES


def test_create_command_returns_404_for_unknown_task() -> None:
    response = client.post(
        "/tasks/task_missing/commands",
        json={"text": "should fail"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_approve_non_approval_command_returns_409() -> None:
    project = client.post("/projects", json={"name": "proj-no-approval"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "task-no-approval"},
    ).json()
    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "quick command", "requires_approval": False},
    ).json()

    response = client.post(
        f"/commands/{accepted['command_id']}/approve",
        json={"approved_by": "owner"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "command does not require approval"


def test_project_active_task_count_refreshes_on_waiting_approval() -> None:
    project = client.post("/projects", json={"name": "proj-active-count"}).json()
    project_id = project["id"]
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "task-active-count"},
    ).json()
    task_id = task["id"]

    first_command = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "first success"},
    )
    assert first_command.status_code == 202
    wait_for_command_terminal_status(first_command.json()["command_id"])

    projects_after_first = client.get("/projects").json()
    project_after_first = next(item for item in projects_after_first if item["id"] == project_id)
    assert project_after_first["active_task_count"] == 0

    waiting_command = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "second requires approval", "requires_approval": True},
    )
    assert waiting_command.status_code == 202
    waiting_id = waiting_command.json()["command_id"]

    projects_waiting = client.get("/projects").json()
    project_waiting = next(item for item in projects_waiting if item["id"] == project_id)
    assert project_waiting["active_task_count"] == 1

    waiting_detail = client.get(f"/commands/{waiting_id}").json()
    assert waiting_detail["status"] == "waiting_approval"

    approved = client.post(
        f"/commands/{waiting_id}/approve",
        json={"approved_by": "owner"},
    )
    assert approved.status_code == 200

    projects_running = client.get("/projects").json()
    project_running = next(item for item in projects_running if item["id"] == project_id)
    assert project_running["active_task_count"] == 1

    wait_for_command_terminal_status(waiting_id)
    projects_done = client.get("/projects").json()
    project_done = next(item for item in projects_done if item["id"] == project_id)
    assert project_done["active_task_count"] == 0
