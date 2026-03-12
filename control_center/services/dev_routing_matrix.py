from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def normalize_text_list(value: object) -> list[str]:
    output: list[str] = []
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, list):
        raw_items = value
    else:
        return output

    for item in raw_items:
        normalized = str(item).strip().lower()
        if not normalized:
            continue
        if normalized not in output:
            output.append(normalized)
    return output


def normalize_task_routing(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}

    output: dict[str, object] = {}
    rule_id = str(value.get("rule_id", "")).strip()
    if rule_id:
        output["rule_id"] = rule_id
    capability_id = str(value.get("capability_id", "")).strip()
    if capability_id:
        output["capability_id"] = capability_id
    executor = str(value.get("executor", "")).strip()
    if executor:
        output["executor"] = executor
    source_rule_id = str(value.get("source_rule_id", "")).strip()
    if source_rule_id:
        output["source_rule_id"] = source_rule_id

    required_checks = normalize_text_list(value.get("required_checks"))
    if required_checks:
        output["required_checks"] = required_checks
    handoff_roles = normalize_text_list(value.get("handoff_roles"))
    if handoff_roles:
        output["handoff_roles"] = handoff_roles

    requires_human_confirmation = value.get("requires_human_confirmation")
    if isinstance(requires_human_confirmation, bool):
        output["requires_human_confirmation"] = requires_human_confirmation

    signals = value.get("signals")
    if isinstance(signals, dict):
        normalized_signals: dict[str, list[str]] = {}
        for key, raw_values in signals.items():
            normalized_values = normalize_text_list(raw_values)
            if normalized_values:
                normalized_signals[str(key)] = normalized_values
        if normalized_signals:
            output["signals"] = normalized_signals

    return output


class DevRoutingMatrixService:
    def __init__(self, matrix_path: str, logger: Any | None = None) -> None:
        self._matrix_path = matrix_path
        self._logger = logger
        self._matrix = self._load_matrix(matrix_path)

    @property
    def matrix(self) -> dict[str, object]:
        return self._matrix

    @property
    def matrix_path(self) -> str:
        return self._matrix_path

    @staticmethod
    def _default_matrix() -> dict[str, object]:
        return {
            "version": "1",
            "default_target": {
                "role": "module-dev",
                "capability_id": "builtin.skill.general-dev",
                "executor": "coding-agent",
            },
            "rules": [],
        }

    def _load_matrix(self, path: str) -> dict[str, object]:
        fallback = self._default_matrix()
        target_path = Path(path)
        try:
            payload = json.loads(target_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            if self._logger is not None:
                self._logger.warning(
                    "dev routing matrix load failed; fallback enabled path=%s reason=%s",
                    path,
                    str(exc),
                )
            return fallback

        if not isinstance(payload, dict):
            if self._logger is not None:
                self._logger.warning(
                    "dev routing matrix root invalid; fallback enabled path=%s",
                    path,
                )
            return fallback

        if not isinstance(payload.get("rules"), list):
            payload["rules"] = []
        if not isinstance(payload.get("default_target"), dict):
            payload["default_target"] = dict(fallback["default_target"])
        payload.setdefault("version", "1")
        payload.setdefault("updated_at", "")
        return payload

    @staticmethod
    def _module_profile_map(chief_metadata: dict[str, object]) -> dict[str, dict[str, object]]:
        if not isinstance(chief_metadata, dict):
            return {}
        decomposition = chief_metadata.get("decomposition")
        if not isinstance(decomposition, dict):
            return {}
        module_items = decomposition.get("modules")
        if not isinstance(module_items, list):
            return {}

        output: dict[str, dict[str, object]] = {}
        for item in module_items:
            if not isinstance(item, dict):
                continue
            module_key = str(item.get("module_key", "")).strip()
            if not module_key:
                continue
            output[module_key] = item
        return output

    @staticmethod
    def _infer_module_routing_signals(
        *,
        module_key: str,
        profile: dict[str, object] | None,
    ) -> dict[str, list[str]]:
        tokens = normalize_text_list(re.split(r"[^a-zA-Z0-9]+", module_key))
        coverage_tags = normalize_text_list(
            profile.get("coverage_tags") if isinstance(profile, dict) else []
        )

        domain = normalize_text_list(profile.get("domain") if isinstance(profile, dict) else [])
        if not domain:
            if any(item in tokens or item in coverage_tags for item in ("frontend", "ui", "web")):
                domain = ["frontend"]
            elif any(item in tokens or item in coverage_tags for item in ("infra", "devops")):
                domain = ["infra"]
            elif any(item in tokens or item in coverage_tags for item in ("security", "auth")):
                domain = ["security"]
            elif any(
                item in tokens or item in coverage_tags
                for item in ("data", "etl", "crawl", "sentiment")
            ):
                domain = ["data"]
            else:
                domain = ["backend"]

        stack = normalize_text_list(profile.get("stack") if isinstance(profile, dict) else [])
        if not stack:
            if any(item in tokens for item in ("react", "nextjs", "next", "vue")):
                stack = ["react"]
            elif any(item in tokens for item in ("fastapi", "flask", "django")):
                stack = ["fastapi"]
            elif any(item in tokens for item in ("go", "gin", "fiber")):
                stack = ["go"]

        language = normalize_text_list(
            profile.get("language") if isinstance(profile, dict) else []
        )
        if not language:
            if any(item in stack for item in ("react", "nextjs", "next", "vue")):
                language = ["typescript"]
            elif any(item in stack for item in ("fastapi", "flask", "django")):
                language = ["python"]
            elif any(item in stack for item in ("go", "gin", "fiber")):
                language = ["go"]
            elif "data" in domain:
                language = ["python", "sql"]

        task_type = normalize_text_list(
            profile.get("task_type") if isinstance(profile, dict) else []
        )
        if not task_type:
            task_type = ["feature"]

        risk = normalize_text_list(profile.get("risk") if isinstance(profile, dict) else [])
        if not risk:
            risk = (
                ["high"]
                if any(
                    item in tokens or item in coverage_tags
                    for item in ("security", "auth", "compliance")
                )
                else ["normal"]
            )

        return {
            "domain": domain,
            "stack": stack,
            "language": language,
            "task_type": task_type,
            "risk": risk,
        }

    @staticmethod
    def _matrix_rule_matches(
        *,
        rule_match: dict[str, object],
        signals: dict[str, list[str]],
    ) -> bool:
        for key, expected_raw in rule_match.items():
            expected = normalize_text_list(expected_raw)
            if not expected:
                continue
            actual = normalize_text_list(signals.get(str(key), []))
            if not actual:
                continue
            if set(actual).isdisjoint(set(expected)):
                return False
        return True

    def _select_rule(
        self,
        *,
        signals: dict[str, list[str]],
    ) -> tuple[str, dict[str, object], list[str], list[str], bool]:
        matrix = self._matrix
        default_target = matrix.get("default_target")
        target = default_target if isinstance(default_target, dict) else {}
        fallback_role = str(target.get("role", "module-dev")).strip().lower() or "module-dev"
        fallback_capability = (
            str(target.get("capability_id", "builtin.skill.general-dev")).strip()
            or "builtin.skill.general-dev"
        )
        fallback_executor = str(target.get("executor", "coding-agent")).strip() or "coding-agent"
        fallback_target = {
            "role": fallback_role,
            "capability_id": fallback_capability,
            "executor": fallback_executor,
        }

        rules = matrix.get("rules")
        if not isinstance(rules, list):
            return "default", fallback_target, [], [], False

        sorted_rules = sorted(
            [item for item in rules if isinstance(item, dict)],
            key=lambda item: int(item.get("priority", 9999))
            if isinstance(item.get("priority"), int)
            else 9999,
        )
        for rule in sorted_rules:
            match = rule.get("match")
            if not isinstance(match, dict):
                continue
            if not self._matrix_rule_matches(rule_match=match, signals=signals):
                continue
            target_raw = rule.get("target")
            if not isinstance(target_raw, dict):
                continue
            role = str(target_raw.get("role", "")).strip().lower()
            capability_id = str(target_raw.get("capability_id", "")).strip()
            executor = str(target_raw.get("executor", "")).strip()
            if not role or not capability_id or not executor:
                continue
            required_checks = normalize_text_list(rule.get("required_checks"))
            handoff_roles = normalize_text_list(rule.get("handoff_roles"))
            requires_human_confirmation = bool(rule.get("requires_human_confirmation", False))
            return (
                str(rule.get("id", "")).strip() or "unnamed-rule",
                {
                    "role": role,
                    "capability_id": capability_id,
                    "executor": executor,
                },
                required_checks,
                handoff_roles,
                requires_human_confirmation,
            )

        return "default", fallback_target, [], [], False

    def apply(
        self,
        *,
        modules: list[str],
        module_task_packages: dict[str, list[dict[str, object]]],
        chief_metadata: dict[str, object],
    ) -> tuple[dict[str, list[dict[str, object]]], dict[str, dict[str, object]]]:
        profile_map = self._module_profile_map(chief_metadata)
        output: dict[str, list[dict[str, object]]] = {}
        decisions: dict[str, dict[str, object]] = {}

        for module in modules:
            tasks = module_task_packages.get(module, [])
            if not isinstance(tasks, list):
                continue
            signals = self._infer_module_routing_signals(
                module_key=module,
                profile=profile_map.get(module),
            )
            (
                rule_id,
                target,
                required_checks,
                handoff_roles,
                requires_human_confirmation,
            ) = self._select_rule(signals=signals)

            target_role = str(target.get("role", "module-dev")).strip().lower() or "module-dev"
            target_capability = str(target.get("capability_id", "")).strip()
            target_executor = str(target.get("executor", "")).strip()
            enriched_tasks: list[dict[str, object]] = []

            for raw_item in tasks:
                if not isinstance(raw_item, dict):
                    continue
                row = dict(raw_item)
                role = str(row.get("role", "")).strip().lower()
                routing = normalize_task_routing(row.get("routing"))

                if role == target_role:
                    routing.setdefault("rule_id", rule_id)
                    if target_capability:
                        routing.setdefault("capability_id", target_capability)
                    if target_executor:
                        routing.setdefault("executor", target_executor)
                    if required_checks:
                        routing.setdefault("required_checks", required_checks)
                    if handoff_roles:
                        routing.setdefault("handoff_roles", handoff_roles)
                    routing.setdefault("signals", signals)
                    if requires_human_confirmation:
                        routing["requires_human_confirmation"] = True
                elif role == "qa-test" and required_checks:
                    routing.setdefault("required_checks", required_checks)
                    routing.setdefault("source_rule_id", rule_id)

                if routing:
                    row["routing"] = routing
                enriched_tasks.append(row)

            output[module] = enriched_tasks
            decisions[module] = {
                "rule_id": rule_id,
                "target": {
                    "role": target_role,
                    "capability_id": target_capability,
                    "executor": target_executor,
                },
                "required_checks": required_checks,
                "handoff_roles": handoff_roles,
                "requires_human_confirmation": requires_human_confirmation,
                "signals": signals,
            }

        return output, decisions
