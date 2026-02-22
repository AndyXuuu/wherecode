import time

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)
FINAL_STATUSES = {"success", "failed", "canceled"}


def wait_for_terminal(command_id: str, timeout: float = 3.0) -> dict:
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
    raise AssertionError(f"command {command_id} did not finish in time, last={last_payload}")


def test_task_status_prefers_failed_when_mixed_terminal_results() -> None:
    project = client.post("/projects", json={"name": "mixed-terminal-project"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "mixed-terminal-task"},
    ).json()
    task_id = task["id"]

    success_command = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "first success command"},
    ).json()
    failed_command = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "second command should fail"},
    ).json()

    success_terminal = wait_for_terminal(success_command["command_id"])
    failed_terminal = wait_for_terminal(failed_command["command_id"])

    assert success_terminal["status"] == "success"
    assert failed_terminal["status"] == "failed"

    task_detail = client.get(f"/tasks/{task_id}")
    assert task_detail.status_code == 200
    assert task_detail.json()["status"] == "failed"

    projects = client.get("/projects").json()
    project_payload = next(item for item in projects if item["id"] == project["id"])
    assert project_payload["active_task_count"] == 0


def test_waiting_approval_precedence_and_release() -> None:
    project = client.post("/projects", json={"name": "approval-priority-project"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "approval-priority-task"},
    ).json()
    task_id = task["id"]

    running_command = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "background success command"},
    ).json()

    waiting_command = client.post(
        f"/tasks/{task_id}/commands",
        json={"text": "approval success command", "requires_approval": True},
    ).json()

    task_waiting = client.get(f"/tasks/{task_id}")
    assert task_waiting.status_code == 200
    assert task_waiting.json()["status"] == "waiting_approval"

    approved = client.post(
        f"/commands/{waiting_command['command_id']}/approve",
        json={"approved_by": "owner"},
    )
    assert approved.status_code == 200

    task_running = client.get(f"/tasks/{task_id}")
    assert task_running.status_code == 200
    assert task_running.json()["status"] in {"in_progress", "done"}

    wait_for_terminal(running_command["command_id"])
    wait_for_terminal(waiting_command["command_id"])

    task_done = client.get(f"/tasks/{task_id}")
    assert task_done.status_code == 200
    assert task_done.json()["status"] == "done"
