import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from control_center.api.v2_report_routes import create_v2_report_router
from control_center.main import app


client = TestClient(app)


def test_v2_report_summary_from_latest_pointer() -> None:
    response = client.get("/reports/v2/summary", params={"subproject": "stock-sentiment"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["subproject_key"] == "stock-sentiment"
    assert isinstance(payload["report_id"], str)
    assert payload["report_id"] != ""
    assert payload["mode"] in {"plan", "build"}
    assert payload["final_status"] in {"success", "failed", "canceled", "succeeded", "error"}
    taxonomy = payload["failure_taxonomy"]
    assert isinstance(taxonomy["code"], str)
    assert isinstance(payload["retry_hints"], list)
    assert isinstance(payload["next_commands"], list)
    assert "compact" in payload
    assert "prioritized_actions" in payload
    assert "primary_action" in payload
    assert isinstance(payload["compact"]["status_line"], str)
    assert "alert_priority" in payload["compact"]
    assert "decision" in payload["compact"]
    assert "primary_action_id" in payload["compact"]
    assert isinstance(payload["prioritized_actions"], list)
    if payload["prioritized_actions"]:
        first = payload["prioritized_actions"][0]
        assert "action_id" in first
        assert "score" in first
        assert "runbook_ref" in first
        assert "can_auto_execute" in first
        assert "requires_confirmation" in first
        assert "estimated_cost" in first


def test_v2_report_summary_accepts_report_argument() -> None:
    latest_path = Path("docs/v2_reports/latest_stock-sentiment_v2_run.json")
    assert latest_path.exists()

    response = client.get(
        "/reports/v2/summary",
        params={"report_path": str(latest_path)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_input"].endswith("latest_stock-sentiment_v2_run.json")
    assert payload["report_path"].endswith(".json")
    assert payload["report_id"] != ""


def test_v2_report_summary_supports_compact_and_max_actions() -> None:
    response = client.get(
        "/reports/v2/summary",
        params={"subproject": "stock-sentiment", "compact": "true", "max_actions": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "compact" in payload
    assert payload["compact"]["status_line"] != ""
    assert isinstance(payload["compact"]["action_required"], bool)
    assert payload["compact"]["alert_priority"] in {"P0", "P1", "P2", "P3"}
    assert payload["compact"]["decision"] in {"act_now", "review_and_run", "observe"}
    assert len(payload["prioritized_actions"]) <= 1


def test_v2_report_summary_supports_action_filters(tmp_path: Path) -> None:
    report = {
        "captured_at": "2026-03-11T00:00:00Z",
        "run": {
            "subproject_key": "stock-sentiment",
            "mode": "plan",
            "final_status": "failed",
        },
        "diagnosis": {
            "failure_taxonomy": {
                "code": "workflow_failed",
                "stage": "execute",
                "severity": "high",
                "reason": "seeded failure",
            },
            "retry_hints": ["rerun", "validate", "check policy"],
            "next_commands": [
                "bash scripts/v2_replay.sh stock-sentiment",
                "bash scripts/check_all.sh v2 --local",
                "bash scripts/stationctl.sh orchestrate-policy",
            ],
        },
    }
    report_path = tmp_path / "v2-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    response = client.get(
        "/reports/v2/summary",
        params={
            "report_path": str(report_path),
            "min_score": 78,
            "action_type": "validate",
            "max_actions": 3,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    actions = payload["prioritized_actions"]
    assert len(actions) == 1
    assert actions[0]["action_type"] == "validate"
    assert actions[0]["score"] >= 78
    assert actions[0]["runbook_ref"] == "ops://check-all-v2"
    assert actions[0]["can_auto_execute"] is True
    assert actions[0]["requires_confirmation"] is True
    assert actions[0]["estimated_cost"] == "low"
    assert payload["primary_action"]["action_id"] == actions[0]["action_id"]
    assert payload["compact"]["primary_action_id"] == actions[0]["action_id"]


def test_v2_report_summary_supports_run_id_lookup(tmp_path: Path) -> None:
    reports_dir = tmp_path / "docs" / "v2_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    target_report = reports_dir / "20260311T010000Z-stock-sentiment-v2-run.json"
    target_report.write_text(
        json.dumps(
            {
                "captured_at": "2026-03-11T01:00:00Z",
                "run": {
                    "subproject_key": "stock-sentiment",
                    "mode": "build",
                    "final_status": "failed",
                },
                "outputs": {"workflow_run_id": "wfr_target_001"},
                "diagnosis": {
                    "failure_taxonomy": {
                        "code": "execution_failed",
                        "stage": "build",
                        "severity": "high",
                        "reason": "seeded failure",
                    },
                    "retry_hints": ["retry once"],
                    "next_commands": ["bash scripts/check_all.sh v2 --local"],
                },
            }
        ),
        encoding="utf-8",
    )

    other_report = reports_dir / "20260311T000000Z-stock-sentiment-v2-run.json"
    other_report.write_text(
        json.dumps(
            {
                "captured_at": "2026-03-11T00:00:00Z",
                "run": {
                    "subproject_key": "stock-sentiment",
                    "mode": "plan",
                    "final_status": "success",
                },
                "outputs": {"workflow_run_id": "wfr_other_001"},
                "diagnosis": {
                    "failure_taxonomy": {
                        "code": "success",
                        "stage": "none",
                        "severity": "none",
                        "reason": "ok",
                    },
                    "retry_hints": ["none"],
                    "next_commands": ["bash scripts/check_all.sh v2"],
                },
            }
        ),
        encoding="utf-8",
    )

    isolated_app = FastAPI()
    isolated_app.include_router(create_v2_report_router(root_dir=tmp_path))
    isolated_client = TestClient(isolated_app)

    response = isolated_client.get(
        "/reports/v2/summary",
        params={"run_id": "wfr_target_001"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["report_path"].endswith("20260311T010000Z-stock-sentiment-v2-run.json")
    assert payload["final_status"] == "failed"


def test_v2_report_summary_supports_report_id_lookup(tmp_path: Path) -> None:
    reports_dir = tmp_path / "docs" / "v2_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = reports_dir / "20260311T030000Z-stock-sentiment-v2-run.json"
    report.write_text(
        json.dumps(
            {
                "captured_at": "2026-03-11T03:00:00Z",
                "run": {
                    "subproject_key": "stock-sentiment",
                    "mode": "plan",
                    "final_status": "success",
                },
                "outputs": {"workflow_run_id": "wfr_report_id_case"},
                "diagnosis": {
                    "failure_taxonomy": {
                        "code": "success",
                        "stage": "none",
                        "severity": "none",
                        "reason": "ok",
                    },
                    "retry_hints": ["none"],
                    "next_commands": ["bash scripts/check_all.sh v2"],
                },
            }
        ),
        encoding="utf-8",
    )

    isolated_app = FastAPI()
    isolated_app.include_router(create_v2_report_router(root_dir=tmp_path))
    isolated_client = TestClient(isolated_app)

    response = isolated_client.get(
        "/reports/v2/summary",
        params={"report_id": "20260311T030000Z-stock-sentiment-v2-run"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["report_id"] == "20260311T030000Z-stock-sentiment-v2-run"
    assert payload["final_status"] == "success"
