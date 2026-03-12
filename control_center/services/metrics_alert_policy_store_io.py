from __future__ import annotations

import json

from control_center.models.hierarchy import now_utc


def load_verify_policy_registry(store) -> None:
    if not store._verify_policy_registry_path.exists():
        store._persist_default_verify_policy_registry()
        return
    try:
        payload = json.loads(store._verify_policy_registry_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            store._persist_default_verify_policy_registry()
            return
        store._verify_policy_registry = store._normalize_verify_policy_registry(payload)
        store._verify_policy_registry_updated_at = now_utc()
    except Exception:  # noqa: BLE001
        store._persist_default_verify_policy_registry()


def persist_default_verify_policy_registry(
    store,
    *,
    default_verify_policy_registry: dict[str, object],
) -> None:
    store._verify_policy_registry = store._normalize_verify_policy_registry(
        dict(default_verify_policy_registry)
    )
    store._verify_policy_registry_updated_at = now_utc()
    store._verify_policy_registry_path.parent.mkdir(parents=True, exist_ok=True)
    store._verify_policy_registry_path.write_text(
        json.dumps(
            store._serialize_verify_policy_registry(dict(store._verify_policy_registry)),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_verify_policy_registry_audits(store) -> list[dict[str, object]]:
    if not store._verify_policy_registry_audit_path.exists():
        return []
    try:
        entries: list[dict[str, object]] = []
        for line in store._verify_policy_registry_audit_path.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            if "id" not in payload:
                continue
            entries.append(store._deserialize_audit(payload))
        return entries
    except Exception:  # noqa: BLE001
        return []


def append_audit_line(path, entry: dict[str, object], *, timestamp_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = dict(entry)
    timestamp = serializable.get(timestamp_key)
    if timestamp is not None and hasattr(timestamp, "isoformat"):
        serializable[timestamp_key] = timestamp.isoformat()
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(serializable, ensure_ascii=False) + "\n")


def load_policy(store) -> None:
    if not store._policy_path.exists():
        store._persist_default_policy()
        return
    try:
        payload = json.loads(store._policy_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            store._persist_default_policy()
            return
        store._policy = store._normalize_policy(payload)
        store._updated_at = now_utc()
    except Exception:  # noqa: BLE001
        store._persist_default_policy()


def persist_default_policy(
    store,
    *,
    default_policy: dict[str, int],
) -> None:
    store._policy = dict(default_policy)
    store._updated_at = now_utc()
    store._policy_path.parent.mkdir(parents=True, exist_ok=True)
    store._policy_path.write_text(
        json.dumps(store._policy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_audits(store) -> list[dict[str, object]]:
    if not store._audit_path.exists():
        return []
    try:
        entries: list[dict[str, object]] = []
        for line in store._audit_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            if "id" not in payload:
                continue
            entries.append(store._deserialize_audit(payload))
        return entries
    except Exception:  # noqa: BLE001
        return []
