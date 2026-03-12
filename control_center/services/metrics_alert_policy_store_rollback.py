from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from control_center.models.hierarchy import now_utc


def is_older_than(
    entry: dict[str, object],
    *,
    seconds: int,
    now,
) -> bool:
    if seconds <= 0:
        return True
    timestamp = entry.get("updated_at") or entry.get("created_at")
    if timestamp is None or not hasattr(timestamp, "tzinfo"):
        return False
    delta = now - timestamp
    return delta.total_seconds() >= seconds


def is_timestamp_after(timestamp, threshold) -> bool:
    if timestamp is None or threshold is None:
        return False
    if not hasattr(timestamp, "tzinfo") or not hasattr(threshold, "tzinfo"):
        return False
    return timestamp >= threshold


def is_timestamp_before(timestamp, threshold) -> bool:
    if timestamp is None or threshold is None:
        return False
    if not hasattr(timestamp, "tzinfo") or not hasattr(threshold, "tzinfo"):
        return False
    return timestamp <= threshold


def find_rollback_approval(
    approvals: list[dict[str, object]],
    approval_id: str,
) -> dict[str, object] | None:
    for entry in approvals:
        if str(entry.get("id", "")).strip() == approval_id:
            return entry
    return None


def refresh_rollback_approval_statuses(
    approvals: list[dict[str, object]],
    *,
    persist: bool,
    persist_handler: Callable[[], None],
) -> int:
    now = now_utc()
    changed = 0
    for entry in approvals:
        status = str(entry.get("status", "")).strip().lower()
        if status not in {"pending", "approved"}:
            continue
        expires_at = entry.get("expires_at")
        if not hasattr(expires_at, "tzinfo"):
            continue
        if expires_at <= now:
            entry["status"] = "expired"
            entry["updated_at"] = now
            changed += 1
    if changed and persist:
        persist_handler()
    return changed


def load_rollback_approvals(
    rollback_approval_path: Path,
    *,
    deserialize_audit: Callable[[dict[str, object]], dict[str, object]],
) -> list[dict[str, object]]:
    if not rollback_approval_path.exists():
        return []
    try:
        approvals: list[dict[str, object]] = []
        for line in rollback_approval_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            if "id" not in payload or "audit_id" not in payload:
                continue
            approvals.append(deserialize_audit(payload))
        return approvals
    except Exception:  # noqa: BLE001
        return []


def persist_rollback_approvals(
    rollback_approval_path: Path,
    approvals: list[dict[str, object]],
) -> None:
    rollback_approval_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for entry in approvals:
        serializable = dict(entry)
        for key in ("created_at", "updated_at", "expires_at"):
            value = serializable.get(key)
            if value is not None and hasattr(value, "isoformat"):
                serializable[key] = value.isoformat()
        lines.append(json.dumps(serializable, ensure_ascii=False))
    payload = "\n".join(lines) + ("\n" if lines else "")
    rollback_approval_path.write_text(payload, encoding="utf-8")


def load_rollback_approval_purge_audits(
    rollback_approval_purge_audit_path: Path,
    *,
    deserialize_audit: Callable[[dict[str, object]], dict[str, object]],
) -> list[dict[str, object]]:
    if not rollback_approval_purge_audit_path.exists():
        return []
    try:
        entries: list[dict[str, object]] = []
        for line in rollback_approval_purge_audit_path.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            if "id" not in payload:
                continue
            entries.append(deserialize_audit(payload))
        return entries
    except Exception:  # noqa: BLE001
        return []


def append_rollback_approval_purge_audit(
    rollback_approval_purge_audit_path: Path,
    entry: dict[str, object],
) -> None:
    rollback_approval_purge_audit_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = dict(entry)
    created_at = serializable.get("created_at")
    if created_at is not None and hasattr(created_at, "isoformat"):
        serializable["created_at"] = created_at.isoformat()
    with rollback_approval_purge_audit_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(serializable, ensure_ascii=False) + "\n")


def persist_rollback_approval_purge_audits(
    rollback_approval_purge_audit_path: Path,
    entries: list[dict[str, object]],
) -> None:
    rollback_approval_purge_audit_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for entry in entries:
        serializable = dict(entry)
        created_at = serializable.get("created_at")
        if created_at is not None and hasattr(created_at, "isoformat"):
            serializable["created_at"] = created_at.isoformat()
        lines.append(json.dumps(serializable, ensure_ascii=False))
    payload = "\n".join(lines) + ("\n" if lines else "")
    rollback_approval_purge_audit_path.write_text(payload, encoding="utf-8")
