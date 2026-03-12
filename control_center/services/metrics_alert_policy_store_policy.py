from __future__ import annotations

from datetime import datetime


def normalize_policy(
    payload: dict[str, object],
    *,
    defaults: dict[str, int],
) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, default_value in defaults.items():
        raw = payload.get(key, default_value)
        value = default_value
        if isinstance(raw, (int, float)):
            value = int(raw)
        elif isinstance(raw, str):
            cleaned = raw.strip()
            if cleaned:
                try:
                    value = int(cleaned)
                except ValueError:
                    value = default_value
        if value < 0:
            value = 0
        normalized[key] = value
    return normalized


def find_rollback_by_request_id(
    audit_entries: list[dict[str, object]],
    request_id: str,
) -> dict[str, object] | None:
    for entry in reversed(audit_entries):
        rollback_request_id = str(entry.get("rollback_request_id", "")).strip()
        if rollback_request_id == request_id:
            return dict(entry)
    return None


def build_rollback_approval_stats(
    approvals: list[dict[str, object]],
) -> dict[str, int]:
    counts: dict[str, int] = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "used": 0,
        "expired": 0,
    }
    for entry in approvals:
        status = str(entry.get("status", "")).strip().lower()
        if status in counts:
            counts[status] += 1
    return {
        "total": len(approvals),
        "pending": counts["pending"],
        "approved": counts["approved"],
        "rejected": counts["rejected"],
        "used": counts["used"],
        "expired": counts["expired"],
    }


def filter_rollback_approvals_by_status(
    approvals: list[dict[str, object]],
    *,
    status: str | None,
) -> list[dict[str, object]]:
    if status is None:
        return approvals
    normalized_status = status.strip().lower()
    return [
        item
        for item in approvals
        if str(item.get("status", "")).strip().lower() == normalized_status
    ]


def compute_rollback_approval_purge_result(
    approvals: list[dict[str, object]],
    *,
    remove_used: bool,
    remove_expired: bool,
    older_than_seconds: int | None,
    now,
    is_older_than_handler,
) -> tuple[list[dict[str, object]], int, int]:
    keep: list[dict[str, object]] = []
    removed_used = 0
    removed_expired = 0
    if older_than_seconds is not None:
        retention_seconds = max(0, int(older_than_seconds))
    else:
        retention_seconds = None
    for entry in approvals:
        status = str(entry.get("status", "")).strip()
        if retention_seconds is not None:
            if not is_older_than_handler(entry, seconds=retention_seconds, now=now):
                keep.append(entry)
                continue
        if status == "used" and remove_used:
            removed_used += 1
            continue
        if status == "expired" and remove_expired:
            removed_expired += 1
            continue
        keep.append(entry)
    return keep, removed_used, removed_expired


def filter_rollback_approval_purge_audits(
    records: list[dict[str, object]],
    *,
    event_type: str | None,
    created_after,
    created_before,
    is_timestamp_after_handler,
    is_timestamp_before_handler,
) -> list[dict[str, object]]:
    output = records
    normalized_event_type = (event_type or "").strip().lower()
    if normalized_event_type:
        output = [
            item
            for item in output
            if str(item.get("event_type", "")).strip().lower() == normalized_event_type
        ]
    if created_after is not None:
        output = [
            item
            for item in output
            if is_timestamp_after_handler(item.get("created_at"), created_after)
        ]
    if created_before is not None:
        output = [
            item
            for item in output
            if is_timestamp_before_handler(item.get("created_at"), created_before)
        ]
    return output


def compute_rollback_approval_purge_audit_gc_result(
    entries: list[dict[str, object]],
    *,
    older_than_seconds: int | None,
    keep_latest: int,
    now,
    is_older_than_handler,
) -> tuple[list[dict[str, object]], int, int]:
    latest_to_keep = max(0, int(keep_latest))
    protected_ids: set[str] = set()
    if latest_to_keep > 0 and entries:
        for entry in entries[-latest_to_keep:]:
            entry_id = str(entry.get("id", "")).strip()
            if entry_id:
                protected_ids.add(entry_id)

    if older_than_seconds is not None:
        retention_seconds = max(0, int(older_than_seconds))
    else:
        retention_seconds = None

    keep: list[dict[str, object]] = []
    removed_total = 0
    for entry in entries:
        entry_id = str(entry.get("id", "")).strip()
        if entry_id and entry_id in protected_ids:
            keep.append(entry)
            continue
        if retention_seconds is not None and not is_older_than_handler(
            entry,
            seconds=retention_seconds,
            now=now,
        ):
            keep.append(entry)
            continue
        removed_total += 1
    return keep, removed_total, latest_to_keep


def deserialize_audit_timestamps(payload: dict[str, object]) -> dict[str, object]:
    entry = dict(payload)
    for key in ("created_at", "updated_at", "expires_at"):
        timestamp = entry.get(key)
        if isinstance(timestamp, str):
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                entry[key] = parsed
            except Exception:  # noqa: BLE001
                pass
    return entry
