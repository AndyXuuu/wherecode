from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _run_gate(
    *,
    tmp_path: Path,
    state_payload: dict[str, object],
    strict: bool = False,
) -> subprocess.CompletedProcess[str]:
    state_file = tmp_path / "state.json"
    milestone_file = tmp_path / "milestones.json"
    state_file.write_text(
        json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    command = ["bash", "scripts/v3_milestone_gate.sh", "--milestone", "test-entry"]
    if strict:
        command.append("--strict")
    return subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_STATE_FILE": str(state_file),
            "WHERECODE_MILESTONE_FILE": str(milestone_file),
        },
        text=True,
        capture_output=True,
    )


def test_v3_milestone_gate_pass_strict(tmp_path: Path) -> None:
    result = _run_gate(
        tmp_path=tmp_path,
        strict=True,
        state_payload={
            "current_sprint": "K50",
            "current_task": "K50-T3",
            "last_completed_task": "K49-T3",
            "last_verified_command": "control_center/.venv/bin/pytest -q",
        },
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout.strip())
    assert payload["passed"] is True
    assert payload["status"] == "passed"
    assert payload["next_phase"] == "TEST-PHASE"
    assert payload["recommended_next_action"] == "start test sprint TST1"

    milestone_file = tmp_path / "milestones.json"
    snapshot = json.loads(milestone_file.read_text(encoding="utf-8"))
    assert snapshot["passed"] is True
    assert snapshot["checks"]["full_pytest_verified"] is True


def test_v3_milestone_gate_pass_with_test_sprint(tmp_path: Path) -> None:
    result = _run_gate(
        tmp_path=tmp_path,
        strict=True,
        state_payload={
            "current_sprint": "TST1",
            "current_task": "TST1-T1",
            "last_completed_task": "K50-T3",
            "last_verified_command": "control_center/.venv/bin/pytest -q",
        },
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout.strip())
    assert payload["passed"] is True
    assert payload["checks"]["current_sprint_at_least_k50"] is True


def test_v3_milestone_gate_blocked_strict(tmp_path: Path) -> None:
    result = _run_gate(
        tmp_path=tmp_path,
        strict=True,
        state_payload={
            "current_sprint": "K50",
            "current_task": "K50-T1",
            "last_completed_task": "K49-T3",
            "last_verified_command": "control_center/.venv/bin/pytest -q tests/unit/test_openapi_contract.py",
        },
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout.strip())
    assert payload["passed"] is False
    assert payload["status"] == "blocked"
    assert "full_pytest_verified" in payload["missing_checks"]


def test_v3_milestone_gate_unsupported_milestone(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "current_sprint": "K50",
                "last_completed_task": "K49-T3",
                "last_verified_command": "control_center/.venv/bin/pytest -q",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_milestone_gate.sh",
            "--milestone",
            "unknown",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_STATE_FILE": str(state_file),
            "WHERECODE_MILESTONE_FILE": str(tmp_path / "milestones.json"),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "unsupported milestone: unknown" in (result.stderr or result.stdout)
