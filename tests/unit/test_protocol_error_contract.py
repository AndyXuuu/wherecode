from fastapi.testclient import TestClient

import control_center.main as main_module
from control_center.main import app


client = TestClient(app)


def _assert_validation_field(response_json: dict, field: str) -> None:
    detail = response_json["detail"]
    assert isinstance(detail, list)
    assert any(item.get("loc", [None])[-1] == field for item in detail)


def test_create_task_unknown_project_returns_404() -> None:
    response = client.post("/projects/proj_missing/tasks", json={"title": "x"})
    assert response.status_code == 404
    assert response.json()["detail"] == "project not found"


def test_list_tasks_unknown_project_returns_404() -> None:
    response = client.get("/projects/proj_missing/tasks")
    assert response.status_code == 404
    assert response.json()["detail"] == "project not found"


def test_get_task_unknown_task_returns_404() -> None:
    response = client.get("/tasks/task_missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_list_commands_unknown_task_returns_404() -> None:
    response = client.get("/tasks/task_missing/commands")
    assert response.status_code == 404
    assert response.json()["detail"] == "task not found"


def test_get_command_unknown_command_returns_404() -> None:
    response = client.get("/commands/cmd_missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "command not found"


def test_approve_unknown_command_returns_404() -> None:
    response = client.post("/commands/cmd_missing/approve", json={"approved_by": "owner"})
    assert response.status_code == 404
    assert response.json()["detail"] == "command not found"


def test_reapprove_command_returns_409_when_not_waiting() -> None:
    project = client.post("/projects", json={"name": "reapprove-contract"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "reapprove-task"},
    ).json()
    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "needs approval", "requires_approval": True},
    ).json()
    command_id = accepted["command_id"]

    first_approve = client.post(
        f"/commands/{command_id}/approve",
        json={"approved_by": "owner"},
    )
    assert first_approve.status_code == 200

    second_approve = client.post(
        f"/commands/{command_id}/approve",
        json={"approved_by": "owner"},
    )
    assert second_approve.status_code == 409
    assert second_approve.json()["detail"] == "command is not waiting approval"


def test_create_project_validation_contract_422() -> None:
    response = client.post("/projects", json={"name": ""})
    assert response.status_code == 422
    _assert_validation_field(response.json(), "name")


def test_create_task_validation_contract_422() -> None:
    project = client.post("/projects", json={"name": "validation-project"}).json()
    response = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": ""},
    )
    assert response.status_code == 422
    _assert_validation_field(response.json(), "title")


def test_create_command_validation_contract_422() -> None:
    project = client.post("/projects", json={"name": "validation-command-project"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "validation-command-task"},
    ).json()
    response = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": ""},
    )
    assert response.status_code == 422
    _assert_validation_field(response.json(), "text")


def test_approve_validation_contract_422() -> None:
    response = client.post("/commands/cmd_any/approve", json={"approved_by": ""})
    assert response.status_code == 422
    _assert_validation_field(response.json(), "approved_by")


def test_auth_unauthorized_contract_401(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "AUTH_ENABLED", True)
    monkeypatch.setattr(main_module, "AUTH_TOKEN", "secure-token")
    response = client.post("/projects", json={"name": "auth-check"})
    assert response.status_code == 401
    assert response.json()["detail"] == "unauthorized"
