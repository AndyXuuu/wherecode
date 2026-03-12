from __future__ import annotations

import json
import logging
from pathlib import Path


logger = logging.getLogger("wherecode.action_layer.agent_rules_registry_loader")


def _normalize_text(value: object) -> str:
    return str(value).strip().lower()


def _normalize_scopes_csv(value: str | None) -> tuple[str, ...]:
    raw = value if value is not None else "subproject,main"
    scopes = tuple(
        scope
        for scope in (_normalize_text(item) for item in raw.split(","))
        if scope
    )
    return scopes or ("subproject", "main")


def load_agent_registry_mapping_from_file(
    registry_path: str,
    *,
    scope_order: str | None = None,
) -> dict[str, str]:
    path = Path(registry_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("agent rules registry must be object")
    raw_scopes = payload.get("scopes")
    if not isinstance(raw_scopes, dict):
        raise ValueError("agent rules registry missing scopes")

    scopes = _normalize_scopes_csv(scope_order)
    mapping: dict[str, str] = {}
    for scope in scopes:
        records = raw_scopes.get(scope)
        if not isinstance(records, list):
            continue
        for item in records:
            if not isinstance(item, dict):
                continue
            role = _normalize_text(item.get("role"))
            executor = _normalize_text(item.get("executor"))
            if role and executor and role not in mapping:
                mapping[role] = executor
    if not mapping:
        raise ValueError("agent rules registry produced empty mapping")
    return mapping


def build_registry_mapping_with_fallback(
    registry_path: str,
    *,
    scope_order: str | None,
    fallback_mapping: dict[str, str],
) -> dict[str, str]:
    try:
        return load_agent_registry_mapping_from_file(
            registry_path,
            scope_order=scope_order,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "agent rules registry load failed, fallback to default mapping: path=%s reason=%s",
            registry_path,
            exc,
        )
        return dict(fallback_mapping)
