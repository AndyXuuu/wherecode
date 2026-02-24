import time

from fastapi.testclient import TestClient

from control_center.main import app


client = TestClient(app)


def wait_terminal(command_id: str, timeout: float = 2.5) -> dict:
    deadline = time.time() + timeout
    payload: dict = {}
    while time.time() < deadline:
        response = client.get(f"/commands/{command_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"success", "failed", "canceled"}:
            return payload
        time.sleep(0.05)
    raise AssertionError(f"command {command_id} not terminal: {payload}")


def test_metrics_summary_includes_rate_and_duration() -> None:
    project = client.post("/projects", json={"name": "metrics-project"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "metrics-task"},
    ).json()

    success = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "run success"},
    )
    assert success.status_code == 202

    failed = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "run fail"},
    )
    assert failed.status_code == 202

    wait_terminal(success.json()["command_id"])
    wait_terminal(failed.json()["command_id"])

    metrics = client.get("/metrics/summary")
    assert metrics.status_code == 200
    payload = metrics.json()

    assert payload["total_projects"] == 1
    assert payload["total_tasks"] == 1
    assert payload["total_commands"] == 2
    assert payload["success_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["success_rate"] == 0.5
    assert payload["average_duration_ms"] >= 0
    assert payload["in_flight_command_count"] == 0
    assert payload["executor_agent_counts"]["coding-agent"] == 2
    assert payload["routing_reason_counts"]["default_agent"] == 2
    assert payload["routing_keyword_counts"] == {}
    assert payload["routing_rule_counts"] == {}
    assert [item["window_minutes"] for item in payload["recent_windows"]] == [5, 15, 60]
    assert payload["recent_windows"][0]["total_commands"] >= 2


def test_metrics_summary_counts_in_flight_and_waiting_approval() -> None:
    project = client.post("/projects", json={"name": "metrics-pending"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "metrics-pending-task"},
    ).json()

    queued = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "queued command"},
    )
    assert queued.status_code == 202

    waiting = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "approval command", "requires_approval": True},
    )
    assert waiting.status_code == 202

    metrics = client.get("/metrics/summary")
    assert metrics.status_code == 200
    payload = metrics.json()

    assert payload["total_commands"] == 2
    assert payload["waiting_approval_count"] == 1
    assert payload["in_flight_command_count"] in {0, 1}


def test_metrics_summary_counts_keyword_and_rule_hits() -> None:
    project = client.post("/projects", json={"name": "metrics-routing"}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "metrics-routing-task"},
    ).json()

    accepted = client.post(
        f"/tasks/{task['id']}/commands",
        json={"text": "please run pytest and coverage"},
    )
    assert accepted.status_code == 202
    wait_terminal(accepted.json()["command_id"])

    metrics = client.get("/metrics/summary")
    assert metrics.status_code == 200
    payload = metrics.json()

    assert payload["routing_reason_counts"]["keyword_rule"] >= 1
    assert payload["routing_keyword_counts"]["pytest"] >= 1
    assert payload["routing_rule_counts"]["rule_test_keywords"] >= 1
    assert payload["recent_windows"][0]["window_minutes"] == 5
