from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from control_center.models.hierarchy import now_utc
from control_center.services.metrics_alert_policy_store import MetricsAlertPolicyStore


def _build_store(tmp_path: Path) -> tuple[MetricsAlertPolicyStore, Path, Path, Path, Path]:
    policy_path = tmp_path / "policy.json"
    audit_path = tmp_path / "audit.jsonl"
    approval_path = tmp_path / "approvals.jsonl"
    purge_audit_path = tmp_path / "approval_purge_audits.jsonl"
    store = MetricsAlertPolicyStore(
        str(policy_path),
        str(audit_path),
        str(approval_path),
        str(purge_audit_path),
        rollback_approval_ttl_seconds=3600,
    )
    return store, policy_path, audit_path, approval_path, purge_audit_path


def _seed_approvals(store: MetricsAlertPolicyStore) -> tuple[str, str, str]:
    store.update_policy(
        {
            "failed_run_delta_gt": 1,
            "failed_run_count_gte": 1,
            "blocked_run_count_gte": 1,
            "waiting_approval_count_gte": 1,
            "in_flight_command_count_gte": 1,
        },
        updated_by="ops-admin",
        reason="seed",
    )
    audit_id = store.list_audits(limit=1)[0]["id"]

    expired = store.create_rollback_approval(audit_id=audit_id, requested_by="ops-admin")
    keep = store.create_rollback_approval(audit_id=audit_id, requested_by="ops-admin")
    used = store.create_rollback_approval(audit_id=audit_id, requested_by="ops-admin")

    store.approve_rollback_approval(keep["id"], approved_by="release-manager")
    store.approve_rollback_approval(used["id"], approved_by="release-manager")
    store.consume_rollback_approval(used["id"], audit_id=audit_id, used_by="ops-admin")

    for entry in store._rollback_approvals:
        if entry["id"] == expired["id"]:
            entry["expires_at"] = now_utc().replace(year=2000)
            break
    store._persist_rollback_approvals()
    return expired["id"], keep["id"], used["id"]


def test_rollback_approval_gc_dry_run(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)

    result = subprocess.run(
        ["bash", "scripts/v3_metrics_rollback_approval_gc.sh", "--dry-run"],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert str(payload["purge_audit_id"]).startswith("rpg_")
    assert payload["removed_expired"] == 1
    assert payload["removed_used"] == 1
    assert payload["remaining_total"] == 1

    lines = approval_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_rollback_approval_gc_apply(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    expired_id, keep_id, used_id = _seed_approvals(store)

    result = subprocess.run(
        ["bash", "scripts/v3_metrics_rollback_approval_gc.sh"],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert str(payload["purge_audit_id"]).startswith("rpg_")
    assert payload["removed_expired"] == 1
    assert payload["removed_used"] == 1
    assert payload["remaining_total"] == 1

    records = [
        json.loads(line)
        for line in approval_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["id"] == keep_id
    assert records[0]["status"] == "approved"
    assert records[0]["id"] != expired_id
    assert records[0]["id"] != used_id


def test_rollback_approval_gc_older_than_window(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    expired_id, keep_id, used_id = _seed_approvals(store)

    now = now_utc()
    for entry in store._rollback_approvals:
        if entry["id"] == expired_id:
            entry["status"] = "expired"
            entry["updated_at"] = now - timedelta(seconds=7200)
        if entry["id"] == used_id:
            entry["updated_at"] = now
    store._persist_rollback_approvals()

    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--older-than-seconds",
            "3600",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert str(payload["purge_audit_id"]).startswith("rpg_")
    assert payload["removed_expired"] == 1
    assert payload["removed_used"] == 0
    assert payload["remaining_total"] == 2

    records = [
        json.loads(line)
        for line in approval_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    remaining_ids = {item["id"] for item in records}
    assert keep_id in remaining_ids
    assert used_id in remaining_ids
    assert expired_id not in remaining_ids


def test_rollback_approval_gc_purge_audits_mode(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(3):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    old_time = now_utc() - timedelta(seconds=7200)
    for idx, entry in enumerate(store._rollback_approval_purge_audits):
        if idx < 2:
            entry["created_at"] = old_time
    store._persist_rollback_approval_purge_audits()

    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--purge-audits",
            "--older-than-seconds",
            "3600",
            "--keep-latest",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert str(payload["purge_audit_gc_id"]).startswith("rpg_")
    assert payload["removed_total"] == 2
    assert payload["remaining_total"] >= 1


def test_rollback_approval_gc_purge_audits_safety_check(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        ["bash", "scripts/v3_metrics_rollback_approval_gc.sh", "--purge-audits"],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "safety check failed" in result.stdout


def test_rollback_approval_gc_export_purge_audits(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    output_path = tmp_path / "exports" / "purge_audits.json"
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert payload["output_path"] == str(output_path)
    assert payload["exported_total"] >= 1

    export_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert export_payload["event_type"] == "approval_purge"
    assert export_payload["exported_total"] >= 1
    checksum = hashlib.sha256(
        json.dumps(export_payload["entries"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert export_payload["checksum_scope"] == "entries"
    assert export_payload["checksum_sha256"] == checksum
    assert all(item["event_type"] == "approval_purge" for item in export_payload["entries"])


def test_rollback_approval_gc_rotate_exports(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    now = now_utc().timestamp()
    old_file_1 = export_dir / "old-1.json"
    old_file_2 = export_dir / "old-2.json"
    new_file = export_dir / "new.json"
    old_file_1.write_text("{}", encoding="utf-8")
    old_file_2.write_text("{}", encoding="utf-8")
    new_file.write_text("{}", encoding="utf-8")
    os.utime(old_file_1, (now - 90000, now - 90000))
    os.utime(old_file_2, (now - 80000, now - 80000))
    os.utime(new_file, (now, now))

    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--rotate-exports",
            "--export-dir",
            str(export_dir),
            "--retain-seconds",
            "86400",
            "--keep-export-latest",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert payload["removed_total"] == 1
    assert payload["remaining_total"] == 2
    assert old_file_1.exists() is False
    assert old_file_2.exists()
    assert new_file.exists()


def test_rollback_approval_gc_rotate_exports_safety_check(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--rotate-exports",
            "--export-dir",
            str(export_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "safety check failed" in result.stdout


def test_rollback_approval_gc_export_manifest_and_verify(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    report_path = tmp_path / "exports" / "verify_report.txt"
    export = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
            "--manifest-key-id",
            "ops-key-1",
            "--manifest-signature",
            "signed-placeholder",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    export_payload = json.loads(export.stdout.strip())
    assert export_payload["manifest_path"] == str(manifest_path)
    assert str(export_payload["manifest_entry_id"]).startswith("exp_")
    manifest_lines = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert manifest_lines[-1]["key_id"] == "ops-key-1"
    assert manifest_lines[-1]["signature"] == "signed-placeholder"

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--verify-report",
            str(report_path),
            "--verify-report-format",
            "txt",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    verify_payload = json.loads(verify.stdout.strip())
    assert verify_payload["verified"] is True
    assert verify_payload["manifest_path"] == str(manifest_path)
    assert verify_payload["output_path"] == str(export_path)
    assert verify_payload["key_id"] == "ops-key-1"
    assert verify_payload["signature_present"] is True
    assert verify_payload["summary"] == "verification passed"
    assert verify_payload["report_path"] == str(report_path)
    assert "Verified: yes" in report_path.read_text(encoding="utf-8")


def test_rollback_approval_gc_verify_manifest_detects_tamper(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
            "--manifest-key-id",
            "ops-key-1",
            "--manifest-signature",
            "signed-placeholder",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    tampered = json.loads(export_path.read_text(encoding="utf-8"))
    if tampered["entries"]:
        tampered["entries"][0]["requested_by"] = "tampered"
    export_path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert verify.returncode != 0
    verify_payload = json.loads(verify.stdout.strip())
    assert verify_payload["verified"] is False
    assert verify_payload["summary"] == "verification failed: checksum mismatch"


def test_rollback_approval_gc_verify_report_requires_verify_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-report",
            str(tmp_path / "report.txt"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "verify-report requires --verify-manifest" in result.stdout


def test_rollback_approval_gc_verify_trend_window_requires_verify_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-trend-window",
            "5",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "verify-trend-window requires --verify-manifest" in result.stdout


def test_rollback_approval_gc_verify_archive_dir_requires_verify_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-archive-dir",
            str(tmp_path / "archive"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "verify-archive-dir requires --verify-manifest" in result.stdout


def test_rollback_approval_gc_verify_fetch_cmd_requires_verify_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-fetch-cmd",
            f"{sys.executable} -c print(1)",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "verify-fetch-cmd requires --verify-manifest" in result.stdout


def test_rollback_approval_gc_verify_policy_requires_verify_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-slo-min-pass-rate",
            "0.9",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "verify policy options require --verify-manifest" in result.stdout


def test_rollback_approval_gc_policy_profile_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--policy-profile",
            "strict",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--policy-profile requires --verify-manifest or --signer-preflight" in result.stdout


def test_rollback_approval_gc_policy_file_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    policy_file = tmp_path / "profile_policy.json"
    policy_file.write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--policy-file",
            str(policy_file),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--policy-file requires --verify-manifest or --signer-preflight" in result.stdout


def test_rollback_approval_gc_policy_source_url_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    policy_file = tmp_path / "policy_source.json"
    policy_file.write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--policy-source-url",
            policy_file.as_uri(),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--policy-source-url requires --verify-manifest or --signer-preflight" in result.stdout


def test_rollback_approval_gc_policy_source_url_conflicts_with_policy_file(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    policy_file = tmp_path / "policy_file.json"
    policy_file.write_text("{}", encoding="utf-8")
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        '{"id":"exp_1","output_path":"missing.json","checksum_sha256":"abc"}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-file",
            str(policy_file),
            "--policy-source-url",
            policy_file.as_uri(),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--policy-file and --policy-source-url cannot be used together" in result.stdout


def test_rollback_approval_gc_distribute_effective_policy_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--distribute-effective-policy-dir",
            str(tmp_path / "policy_distribute"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--distribute-effective-policy-dir requires --verify-manifest or --signer-preflight" in result.stdout


def test_rollback_approval_gc_distribute_effective_policy_retain_requires_dir(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--distribute-effective-policy-retain-seconds",
            "3600",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert (
        "--distribute-effective-policy-retain-seconds requires --distribute-effective-policy-dir"
        in result.stdout
    )


def test_rollback_approval_gc_distribute_effective_policy_keep_latest_requires_dir(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--distribute-effective-policy-keep-latest",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert (
        "--distribute-effective-policy-keep-latest requires --distribute-effective-policy-dir"
        in result.stdout
    )


def test_rollback_approval_gc_list_effective_policy_distributions_requires_dir(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--list-effective-policy-distributions requires --distribute-effective-policy-dir" in result.stdout


def test_rollback_approval_gc_list_effective_policy_distributions_filters_require_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions-mode",
            "verify_manifest",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "list-effective-policy-distributions filters require --list-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_list_effective_policy_fail_on_integrity_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-fail-on-integrity-error",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "list-effective-policy-distributions filters require --list-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_list_effective_policy_state_file_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-state-file",
            str(tmp_path / "list_state.json"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "list-effective-policy-distributions filters require --list-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_list_effective_policy_fail_on_empty_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-fail-on-empty",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "list-effective-policy-distributions filters require --list-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_list_effective_policy_min_selected_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-min-selected",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "list-effective-policy-distributions filters require --list-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_list_effective_policy_min_selected_invalid_value(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_invalid_min_selected"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-min-selected",
            "-1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "invalid --list-effective-policy-min-selected: must be >= 0" in (
        result.stderr or result.stdout
    )


def test_rollback_approval_gc_restore_effective_policy_distributions_requires_dir(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--restore-effective-policy-distributions requires --distribute-effective-policy-dir" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_distributions_filters_require_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions-limit",
            "3",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "restore-effective-policy-distributions filters require --restore-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_verify_integrity_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-verify-integrity",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "restore-effective-policy-distributions filters require --restore-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_fail_on_integrity_requires_verify(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(tmp_path / "dist"),
            "--restore-effective-policy-fail-on-integrity-error",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--restore-effective-policy-fail-on-integrity-error requires --restore-effective-policy-verify-integrity" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_remap_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-remap-from",
            "/old/root",
            "--restore-effective-policy-remap-to",
            "/new/root",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "restore-effective-policy-distributions filters require --restore-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_remap_requires_pair(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(tmp_path / "dist"),
            "--restore-effective-policy-remap-from",
            "/old/root",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--restore-effective-policy-remap-from and --restore-effective-policy-remap-to must be used together" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_state_file_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-state-file",
            str(tmp_path / "state.json"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "restore-effective-policy-distributions filters require --restore-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_min_restored_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-min-restored",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "restore-effective-policy-distributions filters require --restore-effective-policy-distributions" in result.stdout


def test_rollback_approval_gc_restore_effective_policy_min_restored_invalid_value(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_invalid_restore_min"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-min-restored",
            "-1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "invalid --restore-effective-policy-min-restored: must be >= 0" in (
        result.stderr or result.stdout
    )


def test_rollback_approval_gc_export_effective_policy_requires_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-effective-policy",
            str(tmp_path / "effective-policy.json"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "--export-effective-policy requires --verify-manifest or --signer-preflight" in result.stdout


def test_rollback_approval_gc_preflight_slo_requires_preflight_mode(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--preflight-slo-min-pass-rate",
            "1.0",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "preflight slo options require --signer-preflight" in result.stdout


def test_rollback_approval_gc_preflight_slo_requires_history(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer_ok.py"
    signer_script.write_text(
        "import json\nprint(json.dumps({'key_id':'k','signature':'s'}))\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--preflight-slo-min-pass-rate",
            "1.0",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "preflight slo options require --preflight-history" in result.stdout


def test_rollback_approval_gc_preflight_policy_profile_requires_history(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer_ok.py"
    signer_script.write_text(
        "import json\nprint(json.dumps({'key_id':'k','signature':'s'}))\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--policy-profile",
            "strict",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "non-custom --policy-profile in preflight mode requires --preflight-history" in result.stdout


def test_rollback_approval_gc_preflight_history_requires_preflight(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--preflight-history",
            str(tmp_path / "preflight.jsonl"),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "preflight-history/--preflight-history-window require --signer-preflight" in result.stdout


def test_rollback_approval_gc_signer_preflight_success(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer.py"
    signer_script.write_text(
        "import json,sys\n"
        "payload=json.loads(sys.stdin.read() or '{}')\n"
        "probe=str(payload.get('probe',''))\n"
        "print(json.dumps({'key_id':'preflight-key','signature':'sig-'+probe[:8]}))\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert payload["signer_preflight"] is True
    assert payload["success"] is True
    assert payload["key_id"] == "preflight-key"
    assert str(payload["signature_preview"]).startswith("sig-wherecod")


def test_rollback_approval_gc_signer_preflight_history_trend(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer_toggle.py"
    signer_script.write_text(
        "import json, os, sys\n"
        "payload=json.loads(sys.stdin.read() or '{}')\n"
        "mode=os.environ.get('SIGNER_MODE','ok')\n"
        "if mode == 'fail':\n"
        "  print('toggle-fail', file=sys.stderr)\n"
        "  raise SystemExit(8)\n"
        "probe=str(payload.get('probe',''))\n"
        "print(json.dumps({'key_id':'trend-key','signature':'sig-'+probe[:8]}))\n",
        encoding="utf-8",
    )
    history_path = tmp_path / "signer_preflight_history.jsonl"
    base_env = {
        **os.environ,
        "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
        "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
        "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
        "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
    }
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--preflight-history",
            str(history_path),
            "--preflight-history-window",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={**base_env, "SIGNER_MODE": "ok"},
        text=True,
        capture_output=True,
        check=True,
    )
    failed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--preflight-history",
            str(history_path),
            "--preflight-history-window",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={**base_env, "SIGNER_MODE": "fail"},
        text=True,
        capture_output=True,
    )
    assert failed.returncode != 0
    payload = json.loads(failed.stdout.strip())
    assert payload["history_path"] == str(history_path)
    assert payload["history_trend"]["window_size"] == 2
    assert payload["history_trend"]["sample_size"] == 2
    assert payload["history_trend"]["passed_total"] == 1
    assert payload["history_trend"]["failed_total"] == 1
    assert payload["history_trend"]["consecutive_failures"] == 1


def test_rollback_approval_gc_preflight_slo_gate_violation(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer_toggle.py"
    signer_script.write_text(
        "import json, os, sys\n"
        "mode=os.environ.get('SIGNER_MODE','ok')\n"
        "if mode == 'fail':\n"
        "  print('toggle-fail', file=sys.stderr)\n"
        "  raise SystemExit(8)\n"
        "print(json.dumps({'key_id':'trend-key','signature':'sig-ok'}))\n",
        encoding="utf-8",
    )
    history_path = tmp_path / "signer_preflight_history.jsonl"
    base_env = {
        **os.environ,
        "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
        "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
        "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
        "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
    }
    failed_first = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--preflight-history",
            str(history_path),
            "--preflight-history-window",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={**base_env, "SIGNER_MODE": "fail"},
        text=True,
        capture_output=True,
    )
    assert failed_first.returncode != 0

    gated = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--preflight-history",
            str(history_path),
            "--preflight-history-window",
            "2",
            "--preflight-slo-min-pass-rate",
            "1.0",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={**base_env, "SIGNER_MODE": "ok"},
        text=True,
        capture_output=True,
    )
    assert gated.returncode != 0
    payload = json.loads(gated.stdout.strip())
    assert payload["success"] is True
    assert payload["policy_passed"] is False
    assert "slo_violations" in payload


def test_rollback_approval_gc_signer_preflight_failure(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer_fail.py"
    signer_script.write_text(
        "import sys\n"
        "print('boom', file=sys.stderr)\n"
        "raise SystemExit(7)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout.strip())
    assert payload["signer_preflight"] is True
    assert payload["success"] is False
    assert "manifest signer failed (code=7): boom" in payload["summary"]


def test_rollback_approval_gc_signer_preflight_timeout(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    signer_script = tmp_path / "signer_timeout.py"
    signer_script.write_text(
        "import time\n"
        "time.sleep(2)\n"
        "print('{\"key_id\":\"k\",\"signature\":\"s\"}')\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--signer-preflight",
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
            "--manifest-signer-timeout",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout.strip())
    assert payload["signer_preflight"] is True
    assert payload["success"] is False
    assert "manifest signer timeout after 1s" in payload["summary"]


def test_rollback_approval_gc_manifest_signer_hook(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    signer_script = tmp_path / "signer.py"
    signer_script.write_text(
        "import json,sys\n"
        "payload=json.loads(sys.stdin.read() or '{}')\n"
        "checksum=str(payload.get('checksum_sha256',''))\n"
        "print(json.dumps({'key_id':'hook-key-1','signature':'sig-'+checksum[:12]}))\n",
        encoding="utf-8",
    )

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
            "--manifest-signer-cmd",
            f"{sys.executable} {signer_script}",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout.strip())
    assert payload["manifest_signer_used"] is True
    manifest_lines = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert manifest_lines[-1]["key_id"] == "hook-key-1"
    assert str(manifest_lines[-1]["signature"]).startswith("sig-")


def test_rollback_approval_gc_verify_report_json_format(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    report_path = tmp_path / "exports" / "verify_report.json"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--verify-report",
            str(report_path),
            "--verify-report-format",
            "json",
            "--verify-trend-window",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["report_format"] == "json"
    assert payload["trend_summary"]["window_size"] == 1
    assert payload["trend_summary"]["sample_size"] == 1
    assert payload["trend_summary"]["passed_total"] == 1
    assert payload["trend_summary"]["failed_total"] == 0
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_payload["verified"] is True
    assert report_payload["trend_summary"]["window_size"] == 1
    assert report_payload["summary"] == "verification passed"


def test_rollback_approval_gc_verify_policy_file_default_profile(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    policy_file = tmp_path / "policy_profile.json"
    policy_file.write_text(
        json.dumps(
            {
                "default_profile": "standard",
                "profiles": {
                    "standard": {
                        "verify_slo_min_pass_rate": 0.85,
                        "verify_slo_max_fetch_failures": 2,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-file",
            str(policy_file),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["policy_profile"] == "standard"
    assert payload["effective_policy"]["policy_source"] == "policy_file"
    assert payload["effective_policy"]["policy_file"] == str(policy_file)
    assert payload["effective_policy"]["verify_slo_min_pass_rate"] == 0.85


def test_rollback_approval_gc_verify_policy_source_url_default_profile(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    policy_source_file = tmp_path / "policy_source.json"
    policy_source_file.write_text(
        json.dumps(
            {
                "default_profile": "standard",
                "profiles": {
                    "standard": {
                        "verify_slo_min_pass_rate": 0.84,
                        "verify_slo_max_fetch_failures": 2,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    source_url = policy_source_file.as_uri()
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-source-url",
            source_url,
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["policy_profile"] == "standard"
    assert payload["effective_policy"]["policy_source"] == "policy_url"
    assert payload["effective_policy"]["policy_source_url"] == source_url
    assert payload["effective_policy"]["verify_slo_min_pass_rate"] == 0.84


def test_rollback_approval_gc_verify_policy_source_url_with_token_option(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    policy_source_file = tmp_path / "policy_source_with_token.json"
    policy_source_file.write_text(
        json.dumps(
            {
                "default_profile": "standard",
                "profiles": {
                    "standard": {
                        "verify_slo_min_pass_rate": 0.83,
                        "verify_slo_max_fetch_failures": 2,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    source_url = policy_source_file.as_uri()
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-source-url",
            source_url,
            "--policy-source-token",
            "policy-token-1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["policy_profile"] == "standard"
    assert payload["effective_policy"]["policy_source"] == "policy_url"
    assert payload["effective_policy"]["policy_source_url"] == source_url
    assert payload["effective_policy"]["verify_slo_min_pass_rate"] == 0.83


def test_rollback_approval_gc_export_effective_policy_snapshot(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    effective_path = tmp_path / "exports" / "effective_policy.json"
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--export-effective-policy",
            str(effective_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["effective_policy_path"] == str(effective_path)
    snapshot = json.loads(effective_path.read_text(encoding="utf-8"))
    assert snapshot["mode"] == "verify_manifest"
    assert snapshot["effective_policy"]["policy_profile"] == "strict"


def test_rollback_approval_gc_distribute_effective_policy_snapshot(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    distribute_dir = tmp_path / "effective_policy_dist"
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["effective_policy_distribution_dir"] == str(distribute_dir)
    assert payload["effective_policy_distribution_versioned_checksum_sha256"]
    assert payload["effective_policy_distribution_cleanup_enabled"] is False
    assert payload["effective_policy_distribution_removed_total"] == 0
    assert payload["effective_policy_distribution_index_compaction_removed_total"] == 0
    assert payload["effective_policy_distribution_index_archive_appended_total"] == 0
    latest_path = Path(str(payload["effective_policy_distribution_latest"]))
    versioned_path = Path(str(payload["effective_policy_distribution_versioned"]))
    index_path = Path(str(payload["effective_policy_distribution_index_path"]))
    archive_path = Path(str(payload["effective_policy_distribution_index_archive_path"]))
    assert str(payload["effective_policy_distribution_index_entry_id"]).startswith("dist_")
    assert latest_path.exists()
    assert versioned_path.exists()
    assert index_path.exists()
    assert archive_path.exists() is False
    index_entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(index_entries) >= 1
    assert index_entries[-1]["mode"] == "verify_manifest"
    assert index_entries[-1]["versioned_checksum_sha256"] == payload["effective_policy_distribution_versioned_checksum_sha256"]
    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    versioned_payload = json.loads(versioned_path.read_text(encoding="utf-8"))
    assert latest_payload["mode"] == "verify_manifest"
    assert latest_payload["effective_policy"]["policy_profile"] == "strict"
    assert versioned_payload == latest_payload


def test_rollback_approval_gc_distribute_effective_policy_retention_cleanup(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    distribute_dir = tmp_path / "effective_policy_dist_retention"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    old_files = [
        distribute_dir / "effective_policy_verify_manifest_20250101T000001000000+0000.json",
        distribute_dir / "effective_policy_verify_manifest_20250101T000002000000+0000.json",
        distribute_dir / "effective_policy_verify_manifest_20250101T000003000000+0000.json",
    ]
    stale_ts = now_utc().timestamp() - 172800
    for file_path in old_files:
        file_path.write_text("{\"legacy\":true}\n", encoding="utf-8")
        os.utime(file_path, (stale_ts, stale_ts))

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--distribute-effective-policy-keep-latest",
            "1",
            "--distribute-effective-policy-retain-seconds",
            "86400",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["effective_policy_distribution_cleanup_enabled"] is True
    assert payload["effective_policy_distribution_keep_latest"] == 1
    assert payload["effective_policy_distribution_retain_seconds"] == 86400
    assert payload["effective_policy_distribution_removed_total"] == 3
    assert payload["effective_policy_distribution_remaining_versioned_total"] == 1
    assert Path(str(payload["effective_policy_distribution_index_path"])).exists()
    for file_path in old_files:
        assert file_path.exists() is False
    assert Path(str(payload["effective_policy_distribution_versioned"])).exists()


def test_rollback_approval_gc_list_effective_policy_distributions_mode(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    distribute_dir = tmp_path / "effective_policy_dist_list"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-distributions-limit",
            "5",
            "--list-effective-policy-distributions-mode",
            "verify_manifest",
            "--list-effective-policy-distributions-since-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(listed.stdout.strip())
    assert payload["distribution_dir"] == str(distribute_dir)
    assert payload["mode_filter"] == "verify_manifest"
    assert payload["matched_total"] >= 1
    assert len(payload["entries"]) >= 1
    assert payload["entries"][0]["mode"] == "verify_manifest"
    assert payload["integrity_guard_passed"] is True
    assert payload["integrity_failed_total"] == 0
    assert payload["list_safety_risk_level"] == "low"
    assert payload["list_empty_guard_passed"] is True
    assert payload["list_empty_fail_on_error"] is False
    assert payload["list_min_selected"] is None
    assert payload["list_min_selected_guard_passed"] is True
    assert payload["list_recommendations"] == []
    assert payload["summary"].startswith("list completed:")
    assert payload["entries"][0]["integrity_status"] == "ok"
    assert payload["entries"][0]["integrity_ok"] is True


def test_rollback_approval_gc_list_effective_policy_distributions_integrity_mismatch(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    distribute_dir = tmp_path / "effective_policy_dist_integrity"
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    verify_payload = json.loads(verify.stdout.strip())
    versioned_path = Path(str(verify_payload["effective_policy_distribution_versioned"]))
    versioned_path.write_text("{\"tampered\":true}\n", encoding="utf-8")

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-distributions-limit",
            "5",
            "--list-effective-policy-distributions-mode",
            "verify_manifest",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(listed.stdout.strip())
    assert payload["integrity_guard_passed"] is False
    assert payload["integrity_failed_total"] >= 1
    assert payload["list_safety_risk_level"] == "high"
    assert len(payload["list_recommendations"]) >= 1
    assert "failed integrity guard" in payload["summary"]
    assert payload["entries"][0]["integrity_status"] == "checksum_mismatch"


def test_rollback_approval_gc_list_effective_policy_distributions_fail_on_integrity_error(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_integrity_gate"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    index_path = distribute_dir / "distribution-index.jsonl"
    now = now_utc()
    index_path.write_text(
        json.dumps(
            {
                "id": "dist_bad",
                "created_at": now.isoformat(),
                "mode": "verify_manifest",
                "versioned_path": str(distribute_dir / "missing.json"),
                "versioned_checksum_sha256": "missing",
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-fail-on-integrity-error",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert listed.returncode != 0
    payload = json.loads(listed.stdout.strip())
    assert payload["list_integrity_fail_on_error"] is True
    assert payload["integrity_guard_passed"] is False
    assert payload["integrity_failed_total"] == 1
    assert payload["list_safety_risk_level"] == "high"
    assert payload["list_empty_guard_passed"] is True
    assert payload["list_empty_fail_on_error"] is False
    assert payload["list_min_selected"] is None
    assert payload["list_min_selected_guard_passed"] is True
    assert payload["entries"][0]["integrity_status"] == "versioned_file_missing"


def test_rollback_approval_gc_list_effective_policy_distributions_fail_on_empty(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_empty_gate"
    distribute_dir.mkdir(parents=True, exist_ok=True)

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-fail-on-empty",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert listed.returncode != 0
    payload = json.loads(listed.stdout.strip())
    assert payload["matched_total"] == 0
    assert payload["selected_total"] == 0
    assert payload["list_empty_guard_passed"] is False
    assert payload["list_empty_fail_on_error"] is True
    assert payload["list_min_selected"] is None
    assert payload["list_min_selected_guard_passed"] is True
    assert payload["list_safety_risk_level"] == "medium"
    assert payload["summary"] == "list completed: no entries matched filters"
    assert len(payload["list_recommendations"]) >= 1


def test_rollback_approval_gc_list_effective_policy_distributions_min_selected_gate(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_min_selected_gate"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    versioned = distribute_dir / "effective_policy_verify_manifest_1.json"
    versioned.write_text("{\"ok\":true}\n", encoding="utf-8")
    checksum = hashlib.sha256(versioned.read_bytes()).hexdigest()
    index_path = distribute_dir / "distribution-index.jsonl"
    now = now_utc()
    index_path.write_text(
        json.dumps(
            {
                "id": "dist_ok",
                "created_at": now.isoformat(),
                "mode": "verify_manifest",
                "versioned_path": str(versioned),
                "versioned_checksum_sha256": checksum,
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-min-selected",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert listed.returncode != 0
    payload = json.loads(listed.stdout.strip())
    assert payload["matched_total"] == 1
    assert payload["selected_total"] == 1
    assert payload["list_empty_guard_passed"] is True
    assert payload["list_empty_fail_on_error"] is False
    assert payload["list_min_selected"] == 2
    assert payload["list_min_selected_guard_passed"] is False
    assert len(payload["list_recommendations"]) >= 1


def test_rollback_approval_gc_list_effective_policy_state_file_writeback(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_list_state"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    versioned = distribute_dir / "effective_policy_verify_manifest_1.json"
    versioned.write_text("{\"ok\":true}\n", encoding="utf-8")
    checksum = hashlib.sha256(versioned.read_bytes()).hexdigest()
    index_path = distribute_dir / "distribution-index.jsonl"
    state_file = tmp_path / "list_state.json"
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "current_sprint": "K45",
                "current_task": "K45-T2",
                "next_action": "run list gate",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    now = now_utc()
    index_path.write_text(
        json.dumps(
            {
                "id": "dist_ok",
                "created_at": now.isoformat(),
                "mode": "verify_manifest",
                "versioned_path": str(versioned),
                "versioned_checksum_sha256": checksum,
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-state-file",
            str(state_file),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(listed.stdout.strip())
    assert payload["state_file"] == str(state_file)
    assert payload["integrity_guard_passed"] is True
    assert payload["list_safety_risk_level"] == "low"
    assert payload["list_empty_guard_passed"] is True
    assert payload["list_min_selected"] is None
    assert payload["list_min_selected_guard_passed"] is True
    snapshot = json.loads(state_file.read_text(encoding="utf-8"))
    assert snapshot["version"] == 1
    assert snapshot["tool"] == "v3_metrics_rollback_approval_gc"
    assert snapshot["mode"] == "list_effective_policy_distributions"
    assert snapshot["current_sprint"] == "K45"
    assert snapshot["current_task"] == "K45-T2"
    assert snapshot["next_action"] == "run list gate"
    assert snapshot["list"]["integrity_guard_passed"] is True
    assert snapshot["list"]["integrity_failed_total"] == 0
    assert snapshot["list"]["list_safety_risk_level"] == "low"
    assert snapshot["list"]["integrity_fail_on_error"] is False
    assert snapshot["list"]["empty_fail_on_error"] is False
    assert snapshot["list"]["empty_guard_passed"] is True
    assert snapshot["list"]["min_selected"] is None
    assert snapshot["list"]["min_selected_guard_passed"] is True


def test_rollback_approval_gc_list_effective_policy_state_file_invalid_json(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_list_state_invalid"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    versioned = distribute_dir / "effective_policy_verify_manifest_1.json"
    versioned.write_text("{\"ok\":true}\n", encoding="utf-8")
    checksum = hashlib.sha256(versioned.read_bytes()).hexdigest()
    index_path = distribute_dir / "distribution-index.jsonl"
    state_file = tmp_path / "list_state_invalid.json"
    state_file.write_text("{invalid-json\n", encoding="utf-8")
    now = now_utc()
    index_path.write_text(
        json.dumps(
            {
                "id": "dist_ok",
                "created_at": now.isoformat(),
                "mode": "verify_manifest",
                "versioned_path": str(versioned),
                "versioned_checksum_sha256": checksum,
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    listed = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--list-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--list-effective-policy-state-file",
            str(state_file),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert listed.returncode != 0
    assert "invalid state-file json" in (listed.stderr or listed.stdout)


def test_rollback_approval_gc_distribution_index_compaction(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_path = tmp_path / "exports" / "purge_audits.json"
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )

    distribute_dir = tmp_path / "effective_policy_dist_compact"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    index_path = distribute_dir / "distribution-index.jsonl"
    index_lines = []
    for idx in range(510):
        index_lines.append(
            json.dumps(
                {
                    "id": f"dist_seed_{idx}",
                    "created_at": (now_utc() - timedelta(minutes=600 - idx)).isoformat(),
                    "mode": "verify_manifest",
                    "versioned_path": str(distribute_dir / f"effective_policy_seed_{idx}.json"),
                    "versioned_checksum_sha256": "seed",
                    "latest_path": str(distribute_dir / "latest.json"),
                },
                ensure_ascii=False,
            )
        )
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["effective_policy_distribution_index_compaction_max_entries"] == 500
    assert payload["effective_policy_distribution_index_compaction_removed_total"] >= 11
    assert payload["effective_policy_distribution_index_total_after_compaction"] == 500
    assert payload["effective_policy_distribution_index_archive_appended_total"] >= 11
    entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(entries) == 500
    archive_path = Path(str(payload["effective_policy_distribution_index_archive_path"]))
    assert archive_path.exists()
    archived_entries = [
        json.loads(line)
        for line in archive_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(archived_entries) == payload["effective_policy_distribution_index_archive_appended_total"]
    assert all(entry.get("archive_reason") == "index_compaction" for entry in archived_entries)


def test_rollback_approval_gc_restore_effective_policy_distributions(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    index_path = distribute_dir / "distribution-index.jsonl"
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()

    index_entries = [
        {
            "id": "dist_dup",
            "created_at": (now - timedelta(minutes=10)).isoformat(),
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "dup.json"),
            "versioned_checksum_sha256": "dup",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_existing",
            "created_at": (now - timedelta(minutes=5)).isoformat(),
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "existing.json"),
            "versioned_checksum_sha256": "existing",
            "latest_path": str(distribute_dir / "latest.json"),
        },
    ]
    index_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in index_entries) + "\n",
        encoding="utf-8",
    )

    archive_entries = [
        {
            "id": "dist_old",
            "created_at": (now - timedelta(days=10)).isoformat(),
            "archived_at": (now - timedelta(days=9)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "old.json"),
            "versioned_checksum_sha256": "old",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_dup",
            "created_at": (now - timedelta(hours=3)).isoformat(),
            "archived_at": (now - timedelta(hours=2)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "dup_from_archive.json"),
            "versioned_checksum_sha256": "dup_archive",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_new_recent",
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "archived_at": (now - timedelta(minutes=90)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "recent.json"),
            "versioned_checksum_sha256": "recent",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_new_latest",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "archived_at": (now - timedelta(minutes=30)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "latest_from_archive.json"),
            "versioned_checksum_sha256": "latest_from_archive",
            "latest_path": str(distribute_dir / "latest.json"),
        },
    ]
    archive_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in archive_entries) + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-distributions-limit",
            "3",
            "--restore-effective-policy-distributions-since-iso",
            (now - timedelta(hours=3)).isoformat(),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(restore.stdout.strip())
    assert payload["dry_run"] is False
    assert payload["restore_integrity_fail_on_error"] is False
    assert payload["restore_integrity_check_enabled"] is False
    assert payload["distribution_dir"] == str(distribute_dir)
    assert payload["distribution_index_path"] == str(index_path)
    assert payload["distribution_archive_path"] == str(archive_path)
    assert payload["archive_scanned_total"] == 4
    assert payload["restore_candidate_total"] == 3
    assert set(payload["restore_candidate_ids"]) == {
        "dist_dup",
        "dist_new_recent",
        "dist_new_latest",
    }
    assert payload["would_restore_total"] == 2
    assert set(payload["would_restore_ids"]) == {"dist_new_recent", "dist_new_latest"}
    assert payload["restored_total"] == 2
    assert set(payload["restored_ids"]) == {"dist_new_recent", "dist_new_latest"}
    assert payload["skipped_existing_total"] == 1
    assert payload["skipped_existing_ids"] == ["dist_dup"]
    assert payload["integrity_checked_total"] == 0
    assert payload["integrity_failed_total"] == 0
    assert payload["integrity_failed_ids"] == []
    assert payload["integrity_guard_passed"] is True
    assert payload["restore_skipped_integrity_total"] == 0
    assert payload["index_total_after_restore"] == 4
    assert payload["restore_safety_risk_level"] == "high"
    assert (
        "enable --restore-effective-policy-verify-integrity before applying restore"
        in payload["restore_recommendations"]
    )
    assert payload["summary"] == "restore completed: restored 2 entries"
    assert payload["restore_min_restored"] is None
    assert payload["restore_min_restored_guard_passed"] is True
    assert payload["restore_min_restored_effective_count"] == 2

    restored_entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    restored_ids = [str(item.get("id")) for item in restored_entries]
    assert restored_ids.count("dist_dup") == 1
    assert "dist_new_recent" in restored_ids
    assert "dist_new_latest" in restored_ids
    assert "dist_old" not in restored_ids
    for item in restored_entries:
        if item.get("id") in {"dist_new_recent", "dist_new_latest"}:
            assert "archived_at" not in item
            assert "archive_reason" not in item


def test_rollback_approval_gc_restore_effective_policy_distributions_dry_run(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_dry_run"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    index_path = distribute_dir / "distribution-index.jsonl"
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()

    initial_index_entries = [
        {
            "id": "dist_existing",
            "created_at": (now - timedelta(minutes=5)).isoformat(),
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "existing.json"),
            "versioned_checksum_sha256": "existing",
            "latest_path": str(distribute_dir / "latest.json"),
        }
    ]
    index_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in initial_index_entries) + "\n",
        encoding="utf-8",
    )
    archive_entries = [
        {
            "id": "dist_existing",
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "archived_at": (now - timedelta(hours=1)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "existing_from_archive.json"),
            "versioned_checksum_sha256": "existing_archive",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_new_1",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "archived_at": (now - timedelta(minutes=50)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "new_1.json"),
            "versioned_checksum_sha256": "new_1",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_new_2",
            "created_at": (now - timedelta(minutes=40)).isoformat(),
            "archived_at": (now - timedelta(minutes=30)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "new_2.json"),
            "versioned_checksum_sha256": "new_2",
            "latest_path": str(distribute_dir / "latest.json"),
        },
    ]
    archive_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in archive_entries) + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--dry-run",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-distributions-limit",
            "3",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(restore.stdout.strip())
    assert payload["dry_run"] is True
    assert payload["restore_integrity_fail_on_error"] is False
    assert payload["restore_integrity_check_enabled"] is False
    assert payload["restore_candidate_total"] == 3
    assert payload["would_restore_total"] == 2
    assert set(payload["would_restore_ids"]) == {"dist_new_1", "dist_new_2"}
    assert payload["restored_total"] == 0
    assert payload["restored_ids"] == []
    assert payload["skipped_existing_total"] == 1
    assert payload["skipped_existing_ids"] == ["dist_existing"]
    assert payload["integrity_checked_total"] == 0
    assert payload["integrity_failed_total"] == 0
    assert payload["integrity_failed_ids"] == []
    assert payload["integrity_guard_passed"] is True
    assert payload["restore_skipped_integrity_total"] == 0
    assert payload["index_total_after_restore"] == 1
    assert payload["restore_safety_risk_level"] == "low"
    assert (
        "remove --dry-run to apply restore writes after review"
        in payload["restore_recommendations"]
    )
    assert payload["summary"] == "restore dry-run completed: 2 entries would be restored"
    assert payload["restore_min_restored"] is None
    assert payload["restore_min_restored_guard_passed"] is True
    assert payload["restore_min_restored_effective_count"] == 2

    current_entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(current_entries) == 1
    assert current_entries[0]["id"] == "dist_existing"


def test_rollback_approval_gc_restore_effective_policy_distributions_min_restored_gate(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_min_gate"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()
    archive_path.write_text(
        json.dumps(
            {
                "id": "dist_single",
                "created_at": (now - timedelta(minutes=20)).isoformat(),
                "archived_at": (now - timedelta(minutes=10)).isoformat(),
                "archive_reason": "index_compaction",
                "mode": "verify_manifest",
                "versioned_path": str(distribute_dir / "single.json"),
                "versioned_checksum_sha256": "single",
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-min-restored",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert restore.returncode != 0
    payload = json.loads(restore.stdout.strip())
    assert payload["restore_min_restored"] == 2
    assert payload["restore_min_restored_guard_passed"] is False
    assert payload["restore_min_restored_effective_count"] == 1
    assert len(payload["restore_recommendations"]) >= 1


def test_rollback_approval_gc_restore_effective_policy_distributions_min_restored_dry_run_uses_would_restore(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_min_gate_dry"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()
    archive_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "dist_a",
                        "created_at": (now - timedelta(minutes=20)).isoformat(),
                        "archived_at": (now - timedelta(minutes=10)).isoformat(),
                        "archive_reason": "index_compaction",
                        "mode": "verify_manifest",
                        "versioned_path": str(distribute_dir / "a.json"),
                        "versioned_checksum_sha256": "a",
                        "latest_path": str(distribute_dir / "latest.json"),
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "dist_b",
                        "created_at": (now - timedelta(minutes=15)).isoformat(),
                        "archived_at": (now - timedelta(minutes=5)).isoformat(),
                        "archive_reason": "index_compaction",
                        "mode": "verify_manifest",
                        "versioned_path": str(distribute_dir / "b.json"),
                        "versioned_checksum_sha256": "b",
                        "latest_path": str(distribute_dir / "latest.json"),
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--dry-run",
            "--restore-effective-policy-distributions",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-min-restored",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(restore.stdout.strip())
    assert payload["dry_run"] is True
    assert payload["would_restore_total"] == 2
    assert payload["restored_total"] == 0
    assert payload["restore_min_restored"] == 1
    assert payload["restore_min_restored_guard_passed"] is True
    assert payload["restore_min_restored_effective_count"] == 2


def test_rollback_approval_gc_restore_effective_policy_distributions_verify_integrity(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_integrity"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    index_path = distribute_dir / "distribution-index.jsonl"
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()

    existing_entry = {
        "id": "dist_existing",
        "created_at": (now - timedelta(minutes=5)).isoformat(),
        "mode": "verify_manifest",
        "versioned_path": str(distribute_dir / "existing.json"),
        "versioned_checksum_sha256": "existing",
        "latest_path": str(distribute_dir / "latest.json"),
    }
    index_path.write_text(
        json.dumps(existing_entry, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    valid_file = distribute_dir / "valid.json"
    valid_file.write_text("{\"ok\":true}\n", encoding="utf-8")
    valid_checksum = hashlib.sha256(valid_file.read_bytes()).hexdigest()
    mismatch_file = distribute_dir / "mismatch.json"
    mismatch_file.write_text("{\"bad\":true}\n", encoding="utf-8")

    archive_entries = [
        {
            "id": "dist_existing",
            "created_at": (now - timedelta(hours=3)).isoformat(),
            "archived_at": (now - timedelta(hours=2)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "existing_from_archive.json"),
            "versioned_checksum_sha256": "existing_archive",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_valid",
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "archived_at": (now - timedelta(minutes=70)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(valid_file),
            "versioned_checksum_sha256": valid_checksum,
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_missing",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "archived_at": (now - timedelta(minutes=50)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(distribute_dir / "missing.json"),
            "versioned_checksum_sha256": "missing",
            "latest_path": str(distribute_dir / "latest.json"),
        },
        {
            "id": "dist_mismatch",
            "created_at": (now - timedelta(minutes=40)).isoformat(),
            "archived_at": (now - timedelta(minutes=30)).isoformat(),
            "archive_reason": "index_compaction",
            "mode": "verify_manifest",
            "versioned_path": str(mismatch_file),
            "versioned_checksum_sha256": "not-match",
            "latest_path": str(distribute_dir / "latest.json"),
        },
    ]
    archive_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in archive_entries) + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--restore-effective-policy-verify-integrity",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-distributions-limit",
            "10",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(restore.stdout.strip())
    assert payload["restore_integrity_fail_on_error"] is False
    assert payload["restore_integrity_check_enabled"] is True
    assert payload["restore_candidate_total"] == 4
    assert payload["integrity_checked_total"] == 3
    assert payload["integrity_failed_total"] == 2
    assert set(payload["integrity_failed_ids"]) == {"dist_missing", "dist_mismatch"}
    assert payload["integrity_guard_passed"] is False
    assert payload["restore_skipped_integrity_total"] == 2
    assert payload["would_restore_total"] == 1
    assert payload["would_restore_ids"] == ["dist_valid"]
    assert payload["restored_total"] == 1
    assert payload["restored_ids"] == ["dist_valid"]
    assert payload["skipped_existing_total"] == 1
    assert payload["skipped_existing_ids"] == ["dist_existing"]
    assert payload["index_total_after_restore"] == 2
    assert payload["restore_safety_risk_level"] == "medium"
    assert (
        "enable --restore-effective-policy-fail-on-integrity-error for non-zero gate"
        in payload["restore_recommendations"]
    )
    assert payload["summary"] == "restore completed: restored 1 entries"
    assert payload["restore_min_restored"] is None
    assert payload["restore_min_restored_guard_passed"] is True
    assert payload["restore_min_restored_effective_count"] == 1

    index_entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    index_ids = {str(item.get("id")) for item in index_entries}
    assert index_ids == {"dist_existing", "dist_valid"}


def test_rollback_approval_gc_restore_effective_policy_distributions_with_path_remap(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_remap"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    index_path = distribute_dir / "distribution-index.jsonl"
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()

    old_root = tmp_path / "old_host_mount"
    new_root = tmp_path / "new_host_mount"
    old_path = old_root / "nested" / "policy.json"
    new_path = new_root / "nested" / "policy.json"
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text("{\"policy\":\"ok\"}\n", encoding="utf-8")
    new_checksum = hashlib.sha256(new_path.read_bytes()).hexdigest()

    archive_path.write_text(
        json.dumps(
            {
                "id": "dist_remap",
                "created_at": (now - timedelta(minutes=40)).isoformat(),
                "archived_at": (now - timedelta(minutes=30)).isoformat(),
                "archive_reason": "index_compaction",
                "mode": "verify_manifest",
                "versioned_path": str(old_path),
                "versioned_checksum_sha256": new_checksum,
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--restore-effective-policy-verify-integrity",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-remap-from",
            str(old_root),
            "--restore-effective-policy-remap-to",
            str(new_root),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(restore.stdout.strip())
    assert payload["restore_path_remap_enabled"] is True
    assert payload["restore_path_remap_from"] == str(old_root)
    assert payload["restore_path_remap_to"] == str(new_root)
    assert payload["restore_path_remap_applied_total"] == 1
    assert payload["restore_path_remap_applied_ids"] == ["dist_remap"]
    assert payload["integrity_checked_total"] == 1
    assert payload["integrity_failed_total"] == 0
    assert payload["restored_total"] == 1

    index_entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(index_entries) == 1
    assert index_entries[0]["id"] == "dist_remap"
    assert index_entries[0]["versioned_path"] == str(new_path)


def test_rollback_approval_gc_restore_effective_policy_state_file_writeback(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_state"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    state_file = tmp_path / "restore_state.json"
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "current_sprint": "K45",
                "current_task": "K45-T2",
                "next_action": "run restore drill",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    now = now_utc()
    versioned = distribute_dir / "versioned.json"
    versioned.write_text("{\"ok\":true}\n", encoding="utf-8")
    checksum = hashlib.sha256(versioned.read_bytes()).hexdigest()

    archive_path.write_text(
        json.dumps(
            {
                "id": "dist_state",
                "created_at": (now - timedelta(minutes=20)).isoformat(),
                "archived_at": (now - timedelta(minutes=10)).isoformat(),
                "archive_reason": "index_compaction",
                "mode": "verify_manifest",
                "versioned_path": str(versioned),
                "versioned_checksum_sha256": checksum,
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--restore-effective-policy-verify-integrity",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-state-file",
            str(state_file),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(restore.stdout.strip())
    assert payload["state_file"] == str(state_file)
    assert state_file.exists()
    snapshot = json.loads(state_file.read_text(encoding="utf-8"))
    assert snapshot["version"] == 1
    assert snapshot["tool"] == "v3_metrics_rollback_approval_gc"
    assert snapshot["mode"] == "restore_effective_policy_distributions"
    assert snapshot["current_sprint"] == "K45"
    assert snapshot["current_task"] == "K45-T2"
    assert snapshot["next_action"] == "run restore drill"
    assert snapshot["restore"]["restored_total"] == 1
    assert snapshot["restore"]["integrity_guard_passed"] is True
    assert snapshot["restore"]["min_restored"] is None
    assert snapshot["restore"]["min_restored_guard_passed"] is True
    assert snapshot["restore"]["min_restored_effective_count"] == 1


def test_rollback_approval_gc_restore_effective_policy_distributions_fail_on_integrity_error(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    distribute_dir = tmp_path / "effective_policy_dist_restore_integrity_gate"
    distribute_dir.mkdir(parents=True, exist_ok=True)
    archive_path = distribute_dir / "distribution-index-archive.jsonl"
    now = now_utc()
    archive_path.write_text(
        json.dumps(
            {
                "id": "dist_bad",
                "created_at": (now - timedelta(minutes=30)).isoformat(),
                "archived_at": (now - timedelta(minutes=20)).isoformat(),
                "archive_reason": "index_compaction",
                "mode": "verify_manifest",
                "versioned_path": str(distribute_dir / "missing.json"),
                "versioned_checksum_sha256": "missing",
                "latest_path": str(distribute_dir / "latest.json"),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    restore = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--restore-effective-policy-distributions",
            "--restore-effective-policy-verify-integrity",
            "--restore-effective-policy-fail-on-integrity-error",
            "--distribute-effective-policy-dir",
            str(distribute_dir),
            "--restore-effective-policy-distributions-limit",
            "5",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert restore.returncode != 0
    payload = json.loads(restore.stdout.strip())
    assert payload["restore_integrity_fail_on_error"] is True
    assert payload["integrity_guard_passed"] is False
    assert payload["integrity_failed_total"] == 1
    assert payload["restored_total"] == 0
    assert payload["restore_safety_risk_level"] == "low"
    assert payload["restore_recommendations"] == [
        "adjust restore since/limit filters to include restorable entries"
    ]
    assert payload["summary"] == "restore completed: no entries restored"


def test_rollback_approval_gc_verify_manifest_archive_fallback(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_dir = tmp_path / "exports"
    archive_dir = tmp_path / "archive"
    export_path = export_dir / "purge_audits.json"
    manifest_path = export_dir / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    archive_dir.mkdir(parents=True, exist_ok=True)
    moved_path = archive_dir / export_path.name
    export_path.rename(moved_path)

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--verify-archive-dir",
            str(archive_dir),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["output_path"] == str(moved_path)
    assert payload["resolved_from"] == "archive_basename_fallback"


def test_rollback_approval_gc_verify_allowed_resolvers_blocks_archive(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_dir = tmp_path / "exports"
    archive_dir = tmp_path / "archive"
    export_path = export_dir / "purge_audits.json"
    manifest_path = export_dir / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    archive_dir.mkdir(parents=True, exist_ok=True)
    moved_path = archive_dir / export_path.name
    export_path.rename(moved_path)

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--verify-archive-dir",
            str(archive_dir),
            "--verify-allowed-resolvers",
            "manifest_output_path,fetch_hook",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert verify.returncode != 0
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is False
    assert "resolver not allowed" in payload["summary"]


def test_rollback_approval_gc_verify_manifest_fetch_hook_fallback(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_dir = tmp_path / "exports"
    export_path = export_dir / "purge_audits.json"
    manifest_path = export_dir / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    exported_payload = json.loads(export_path.read_text(encoding="utf-8"))
    export_path.unlink()
    remote_uri = "https://archive.example.com/purge_audits.json"
    manifest_lines = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest_lines[-1]["output_path"] = remote_uri
    manifest_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in manifest_lines) + "\n",
        encoding="utf-8",
    )

    fetched_path = tmp_path / "fetched" / "remote_export.json"
    fetched_path.parent.mkdir(parents=True, exist_ok=True)
    fetched_path.write_text(json.dumps(exported_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fetch_script = tmp_path / "fetch_hook.py"
    fetch_script.write_text(
        "import json, os, sys\n"
        "payload=json.loads(sys.stdin.read() or '{}')\n"
        "uri=str(payload.get('uri',''))\n"
        "expected=os.environ.get('EXPECTED_URI','')\n"
        "path=os.environ.get('FETCH_LOCAL_PATH','')\n"
        "if expected and uri != expected:\n"
        "  print('uri mismatch', file=sys.stderr)\n"
        "  raise SystemExit(9)\n"
        "print(json.dumps({'local_path': path}))\n",
        encoding="utf-8",
    )

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "degraded",
            "--verify-fetch-cmd",
            f"{sys.executable} {fetch_script}",
            "--verify-fetch-timeout",
            "5",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "EXPECTED_URI": remote_uri,
            "FETCH_LOCAL_PATH": str(fetched_path),
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["resolved_from"] == "fetch_hook"
    assert payload["output_path"] == str(fetched_path)
    assert payload["policy_profile"] == "degraded"
    assert "fetch_hook" in (payload["effective_policy"]["allowed_resolvers"] or [])
    assert payload["verify_fetch_cmd"] is not None


def test_rollback_approval_gc_verify_policy_profile_strict_blocks_fetch_hook(tmp_path: Path) -> None:
    store, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    _seed_approvals(store)
    for _ in range(2):
        store.purge_rollback_approvals(dry_run=True, requested_by="ops-admin")

    export_dir = tmp_path / "exports"
    export_path = export_dir / "purge_audits.json"
    manifest_path = export_dir / "manifest.jsonl"
    subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--export-purge-audits",
            "--event-type",
            "approval_purge",
            "--from-iso",
            (now_utc() - timedelta(days=1)).isoformat(),
            "--limit",
            "50",
            "--output",
            str(export_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
        check=True,
    )
    exported_payload = json.loads(export_path.read_text(encoding="utf-8"))
    export_path.unlink()
    remote_uri = "https://archive.example.com/purge_audits.json"
    manifest_lines = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest_lines[-1]["output_path"] = remote_uri
    manifest_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in manifest_lines) + "\n",
        encoding="utf-8",
    )

    fetched_path = tmp_path / "fetched" / "remote_export.json"
    fetched_path.parent.mkdir(parents=True, exist_ok=True)
    fetched_path.write_text(json.dumps(exported_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fetch_script = tmp_path / "fetch_hook.py"
    fetch_script.write_text(
        "import json, os, sys\n"
        "payload=json.loads(sys.stdin.read() or '{}')\n"
        "uri=str(payload.get('uri',''))\n"
        "expected=os.environ.get('EXPECTED_URI','')\n"
        "path=os.environ.get('FETCH_LOCAL_PATH','')\n"
        "if expected and uri != expected:\n"
        "  print('uri mismatch', file=sys.stderr)\n"
        "  raise SystemExit(9)\n"
        "print(json.dumps({'local_path': path}))\n",
        encoding="utf-8",
    )
    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--policy-profile",
            "strict",
            "--verify-fetch-cmd",
            f"{sys.executable} {fetch_script}",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "EXPECTED_URI": remote_uri,
            "FETCH_LOCAL_PATH": str(fetched_path),
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert verify.returncode != 0
    payload = json.loads(verify.stdout.strip())
    assert payload["policy_profile"] == "strict"
    assert payload["resolved_from"] == "fetch_hook"
    assert payload["policy_passed"] is False
    assert payload["verified"] is False
    assert "resolver not allowed: fetch_hook" in payload["summary"]


def test_rollback_approval_gc_verify_fetch_slo_gate_violation(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    valid_entries = [{"id": "evt_1", "event_type": "approval_purge"}]
    valid_checksum = hashlib.sha256(
        json.dumps(valid_entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    valid_export = tmp_path / "valid_export.json"
    valid_export.write_text(
        json.dumps(
            {
                "entries": valid_entries,
                "checksum_scope": "entries",
                "checksum_sha256": valid_checksum,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "exp_1",
                        "output_path": "https://archive.example.com/missing.json",
                        "checksum_sha256": valid_checksum,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "exp_2",
                        "output_path": str(valid_export),
                        "checksum_sha256": valid_checksum,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    fetch_script = tmp_path / "fetch_hook.py"
    fetch_script.write_text(
        "import json, sys\n"
        "payload=json.loads(sys.stdin.read() or '{}')\n"
        "uri=str(payload.get('uri',''))\n"
        "if uri.endswith('/missing.json'):\n"
        "  print('missing remote', file=sys.stderr)\n"
        "  raise SystemExit(11)\n"
        "print(json.dumps({'local_path':'/tmp/unused.json'}))\n",
        encoding="utf-8",
    )

    verify = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--verify-fetch-cmd",
            f"{sys.executable} {fetch_script}",
            "--verify-slo-max-fetch-failures",
            "0",
            "--verify-trend-window",
            "2",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert verify.returncode != 0
    payload = json.loads(verify.stdout.strip())
    assert payload["verified"] is True
    assert payload["policy_passed"] is False
    assert payload["trend_summary"]["fetch_failure_total"] >= 1
    assert "slo_violations" in payload


def test_rollback_approval_gc_verify_report_invalid_format(tmp_path: Path) -> None:
    _, policy_path, audit_path, approval_path, purge_audit_path = _build_store(tmp_path)
    manifest_path = tmp_path / "exports" / "manifest.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        '{"id":"exp_1","output_path":"missing.json","checksum_sha256":"abc"}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "bash",
            "scripts/v3_metrics_rollback_approval_gc.sh",
            "--verify-manifest",
            "--manifest",
            str(manifest_path),
            "--verify-report-format",
            "yaml",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            **os.environ,
            "WHERECODE_METRICS_ALERT_POLICY_FILE": str(policy_path),
            "WHERECODE_METRICS_ALERT_AUDIT_FILE": str(audit_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE": str(approval_path),
            "WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE": str(purge_audit_path),
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "verify-report-format must be txt or json" in result.stdout
