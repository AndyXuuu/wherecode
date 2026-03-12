#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


VALID_TYPES = {"agent", "mcp", "skill"}
VALID_STATUS = {"draft", "active", "disabled"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
REQUIRED_FIELDS = {
    "id",
    "type",
    "version",
    "owner",
    "status",
    "entry",
    "runtime",
    "input_schema",
    "output_schema",
    "error_contract",
    "permission_contract",
    "cost_budget",
    "observability",
    "compatibility",
}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid json: {path}: {exc}") from None


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_manifest(payload: dict[str, Any], source: str) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        errors.append(f"{source}: missing fields: {', '.join(missing)}")
        return errors

    _require(
        isinstance(payload.get("id"), str) and len(payload["id"]) >= 3,
        f"{source}: id must be string length >= 3",
        errors,
    )
    _require(
        payload.get("type") in VALID_TYPES,
        f"{source}: type must be one of {sorted(VALID_TYPES)}",
        errors,
    )
    _require(
        isinstance(payload.get("version"), str) and SEMVER_RE.match(payload["version"]) is not None,
        f"{source}: version must follow semver x.y.z",
        errors,
    )
    _require(
        isinstance(payload.get("owner"), str) and len(payload["owner"]) > 0,
        f"{source}: owner must be non-empty string",
        errors,
    )
    _require(
        payload.get("status") in VALID_STATUS,
        f"{source}: status must be one of {sorted(VALID_STATUS)}",
        errors,
    )

    entry = payload.get("entry")
    _require(isinstance(entry, dict), f"{source}: entry must be object", errors)
    if isinstance(entry, dict):
        _require(isinstance(entry.get("kind"), str) and bool(entry.get("kind")), f"{source}: entry.kind required", errors)
        _require(isinstance(entry.get("path"), str) and bool(entry.get("path")), f"{source}: entry.path required", errors)

    runtime = payload.get("runtime")
    _require(isinstance(runtime, dict), f"{source}: runtime must be object", errors)
    if isinstance(runtime, dict):
        _require(
            isinstance(runtime.get("engine"), str) and bool(runtime.get("engine")),
            f"{source}: runtime.engine required",
            errors,
        )

    return errors


def validate_registry(payload: dict[str, Any], source: str) -> list[str]:
    errors: list[str] = []
    _require(isinstance(payload, dict), f"{source}: registry must be object", errors)
    if not isinstance(payload, dict):
        return errors

    _require("registry_version" in payload, f"{source}: missing registry_version", errors)
    _require("packages" in payload, f"{source}: missing packages", errors)
    packages = payload.get("packages")
    _require(isinstance(packages, list), f"{source}: packages must be list", errors)
    if isinstance(packages, list):
        for idx, item in enumerate(packages):
            if not isinstance(item, dict):
                errors.append(f"{source}: packages[{idx}] must be object")
                continue
            errors.extend(validate_manifest(item, f"{source}:packages[{idx}]"))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate WhereCode capability manifests/registry.")
    parser.add_argument(
        "--registry",
        default="control_center/capabilities/registry.json",
        help="registry file path",
    )
    parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="manifest file path (repeatable)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_errors: list[str] = []

    registry_path = Path(args.registry)
    try:
        registry_payload = _load_json(registry_path)
    except ValueError as exc:
        print(f"[capability-contract-check] {exc}")
        return 1
    if not isinstance(registry_payload, dict):
        all_errors.append(f"{registry_path}: registry root must be object")
    else:
        all_errors.extend(validate_registry(registry_payload, str(registry_path)))

    for manifest_path_text in args.manifest:
        manifest_path = Path(manifest_path_text)
        try:
            manifest_payload = _load_json(manifest_path)
        except ValueError as exc:
            all_errors.append(str(exc))
            continue
        if not isinstance(manifest_payload, dict):
            all_errors.append(f"{manifest_path}: manifest root must be object")
            continue
        all_errors.extend(validate_manifest(manifest_payload, str(manifest_path)))

    if all_errors:
        for message in all_errors:
            print(f"[capability-contract-check] {message}")
        return 1

    print("[capability-contract-check] ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
