#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = {"version", "updated_at", "default_target", "rules"}
REQUIRED_MATCH_KEYS = {"domain", "task_type"}
REQUIRED_TARGET_KEYS = {"role", "capability_id", "executor"}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid json: {path}: {exc}") from None


def validate_matrix(payload: dict[str, Any], source: str) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - payload.keys())
    if missing:
        errors.append(f"{source}: missing top-level fields: {', '.join(missing)}")
        return errors

    if not isinstance(payload.get("rules"), list):
        errors.append(f"{source}: rules must be list")
        return errors

    default_target = payload.get("default_target")
    if not isinstance(default_target, dict):
        errors.append(f"{source}: default_target must be object")
    else:
        default_missing = sorted(REQUIRED_TARGET_KEYS - default_target.keys())
        if default_missing:
            errors.append(
                f"{source}: default_target missing fields: {', '.join(default_missing)}"
            )

    seen_ids: set[str] = set()
    for idx, rule in enumerate(payload["rules"]):
        pointer = f"{source}:rules[{idx}]"
        if not isinstance(rule, dict):
            errors.append(f"{pointer}: must be object")
            continue

        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            errors.append(f"{pointer}: id must be non-empty string")
        elif rule_id in seen_ids:
            errors.append(f"{pointer}: duplicated id: {rule_id}")
        else:
            seen_ids.add(rule_id)

        priority = rule.get("priority")
        if not isinstance(priority, int):
            errors.append(f"{pointer}: priority must be integer")

        match = rule.get("match")
        if not isinstance(match, dict):
            errors.append(f"{pointer}: match must be object")
        else:
            match_missing = sorted(REQUIRED_MATCH_KEYS - match.keys())
            if match_missing:
                errors.append(f"{pointer}: match missing fields: {', '.join(match_missing)}")
            for key, value in match.items():
                if not isinstance(value, list) or not value:
                    errors.append(f"{pointer}: match.{key} must be non-empty list")

        target = rule.get("target")
        if not isinstance(target, dict):
            errors.append(f"{pointer}: target must be object")
        else:
            target_missing = sorted(REQUIRED_TARGET_KEYS - target.keys())
            if target_missing:
                errors.append(f"{pointer}: target missing fields: {', '.join(target_missing)}")

        checks = rule.get("required_checks")
        if not isinstance(checks, list) or not checks:
            errors.append(f"{pointer}: required_checks must be non-empty list")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate developer routing matrix.")
    parser.add_argument(
        "--matrix",
        default="control_center/capabilities/dev_routing_matrix.json",
        help="routing matrix file path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.matrix)
    try:
        payload = _load_json(path)
    except ValueError as exc:
        print(f"[dev-routing-matrix-check] {exc}")
        return 1

    if not isinstance(payload, dict):
        print(f"[dev-routing-matrix-check] {path}: root must be object")
        return 1

    errors = validate_matrix(payload, str(path))
    if errors:
        for message in errors:
            print(f"[dev-routing-matrix-check] {message}")
        return 1

    print("[dev-routing-matrix-check] ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
