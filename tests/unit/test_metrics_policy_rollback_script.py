from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _write_audit_file(path: Path) -> None:
    entries = [
        {
            "id": "map_old",
            "updated_at": "2026-03-01T00:00:00Z",
            "updated_by": "ops-admin",
            "reason": "seed",
            "policy": {
                "failed_run_delta_gt": 0,
                "failed_run_count_gte": 1,
                "blocked_run_count_gte": 2,
                "waiting_approval_count_gte": 10,
                "in_flight_command_count_gte": 50,
            },
        },
        {
            "id": "map_new",
            "updated_at": "2026-03-01T00:10:00Z",
            "updated_by": "ops-admin",
            "reason": "tighten",
            "policy": {
                "failed_run_delta_gt": 2,
                "failed_run_count_gte": 3,
                "blocked_run_count_gte": 4,
                "waiting_approval_count_gte": 12,
                "in_flight_command_count_gte": 60,
            },
        },
    ]
    payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n"
    path.write_text(payload, encoding="utf-8")


def test_metrics_policy_rollback_dry_run(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    audit_path = tmp_path / "audit.jsonl"
    policy_path.write_text(json.dumps({"failed_run_delta_gt": 9}) + "\n", encoding="utf-8")
    _write_audit_file(audit_path)

    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_policy_rollback.sh",
            "map_old",
            "--dry-run",
            "--local-file-mode",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    assert "dry-run: no file changes applied" in result.stdout
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    assert policy["failed_run_delta_gt"] == 9
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_metrics_policy_rollback_apply(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    audit_path = tmp_path / "audit.jsonl"
    policy_path.write_text(json.dumps({"failed_run_delta_gt": 9}) + "\n", encoding="utf-8")
    _write_audit_file(audit_path)

    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_policy_rollback.sh",
            "map_old",
            "--local-file-mode",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "METRICS_POLICY_ROLLBACK_UPDATED_BY": "ops-admin",
            "METRICS_POLICY_ROLLBACK_REASON": "rollback test",
        },
        text=True,
        capture_output=True,
        check=True,
    )
    assert "rollback applied" in result.stdout

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    assert policy["failed_run_delta_gt"] == 0
    assert policy["failed_run_count_gte"] == 1

    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    appended = json.loads(lines[-1])
    assert appended["rollback_from_audit_id"] == "map_old"
    assert appended["updated_by"] == "ops-admin"
