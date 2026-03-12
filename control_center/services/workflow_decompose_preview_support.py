from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime

from control_center.models import (
    DecomposeBootstrapPreviewResponse,
    DecomposeBootstrapPreviewTask,
    WorkflowRun,
)


class WorkflowDecomposePreviewSupportService:
    def __init__(
        self,
        *,
        normalize_module_candidates_handler: Callable[[list[object]], list[str]],
        extract_modules_from_metadata_handler: Callable[[dict[str, object]], list[str]],
        validate_module_task_packages_handler: Callable[
            [list[str], dict[str, object]],
            tuple[
                dict[str, list[dict[str, object]]],
                list[str],
                dict[str, list[str]],
                dict[str, list[str]],
                bool,
            ],
        ],
        optional_text_handler: Callable[[object], str | None],
        now_utc_handler: Callable[[], datetime],
        persist_run_handler: Callable[[str], object],
    ) -> None:
        self._normalize_module_candidates_handler = normalize_module_candidates_handler
        self._extract_modules_from_metadata_handler = extract_modules_from_metadata_handler
        self._validate_module_task_packages_handler = (
            validate_module_task_packages_handler
        )
        self._optional_text_handler = optional_text_handler
        self._now_utc_handler = now_utc_handler
        self._persist_run_handler = persist_run_handler

    @staticmethod
    def _normalize_preview_depends_on_roles(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        output: list[str] = []
        for item in value:
            role = str(item).strip().lower()
            if not role:
                continue
            if role not in output:
                output.append(role)
        return output

    def get_pending_decomposition(self, run: WorkflowRun) -> dict[str, object] | None:
        pending = run.metadata.get("pending_decomposition")
        if isinstance(pending, dict):
            return pending
        return None

    def get_pending_confirmation_status(self, pending: dict[str, object]) -> str:
        confirmation = pending.get("confirmation")
        if isinstance(confirmation, dict):
            value = str(confirmation.get("status", "")).strip().lower()
            if value:
                return value
        return "unknown"

    def select_decomposition_for_preview(
        self,
        run: WorkflowRun,
    ) -> tuple[dict[str, object] | None, str]:
        pending = self.get_pending_decomposition(run)
        if pending is not None:
            return pending, "pending"

        chief = run.metadata.get("chief_decomposition")
        if isinstance(chief, dict):
            return chief, "chief"

        return None, "none"

    def extract_preview_modules(self, decomposition: dict[str, object]) -> list[str]:
        raw_modules = decomposition.get("modules")
        if isinstance(raw_modules, list):
            modules = self._normalize_module_candidates_handler(raw_modules)
            if modules:
                return modules

        raw_chief_metadata = decomposition.get("chief_metadata")
        if isinstance(raw_chief_metadata, dict):
            return self._extract_modules_from_metadata_handler(raw_chief_metadata)
        return []

    def build_decompose_bootstrap_preview(
        self,
        *,
        run_id: str,
        source: str,
        generated_at: str,
        fingerprint: str,
        decomposition: dict[str, object],
    ) -> DecomposeBootstrapPreviewResponse:
        modules = self.extract_preview_modules(decomposition)
        if not modules:
            raise ValueError("decomposition preview unavailable: no modules")

        (
            module_task_packages,
            missing_task_package_modules,
            invalid_task_package_roles,
            missing_task_package_roles,
            _task_package_explicit,
        ) = self._validate_module_task_packages_handler(
            modules,
            decomposition,
        )

        warnings: list[str] = []
        if missing_task_package_modules:
            warnings.append(
                "missing_task_package_modules="
                + ",".join(sorted(missing_task_package_modules))
            )
        for module_key, roles in sorted(invalid_task_package_roles.items()):
            warnings.append(f"invalid_roles:{module_key}=>{','.join(sorted(roles))}")
        for module_key, roles in sorted(missing_task_package_roles.items()):
            warnings.append(f"missing_roles:{module_key}=>{','.join(sorted(roles))}")

        tasks: list[DecomposeBootstrapPreviewTask] = []
        levels: dict[str, int] = {}
        terminal_task_keys: list[str] = []

        for module in modules:
            package = module_task_packages.get(module, [])
            role_latest_task_key: dict[str, str] = {}
            module_task_keys: list[str] = []

            for index, item in enumerate(package, start=1):
                role = str(item.get("role", "")).strip().lower()
                objective = str(item.get("objective", "")).strip()
                if not role or not objective:
                    continue

                task_key = f"{module}:{index}:{role}"
                depends_on_roles = self._normalize_preview_depends_on_roles(
                    item.get("depends_on_roles")
                )

                depends_on_task_keys: list[str] = []
                for depends_role in depends_on_roles:
                    matched = role_latest_task_key.get(depends_role)
                    if matched:
                        if matched not in depends_on_task_keys:
                            depends_on_task_keys.append(matched)
                    else:
                        warnings.append(
                            f"depends_on_role_missing:{module}:{role}:{depends_role}:fallback=sequence"
                        )
                if not depends_on_task_keys and module_task_keys:
                    depends_on_task_keys = [module_task_keys[-1]]

                level = 0
                for dependency_key in depends_on_task_keys:
                    level = max(level, levels.get(dependency_key, 0) + 1)
                levels[task_key] = level

                priority_value = item.get("priority")
                priority = int(priority_value) if isinstance(priority_value, int) else 3
                if priority < 1 or priority > 5:
                    priority = 3

                deliverable = self._optional_text_handler(item.get("deliverable"))
                task = DecomposeBootstrapPreviewTask(
                    task_key=task_key,
                    phase="module",
                    module_key=module,
                    role=role,
                    objective=objective,
                    priority=priority,
                    deliverable=deliverable,
                    depends_on_roles=depends_on_roles,
                    depends_on_task_keys=depends_on_task_keys,
                    level=level,
                )
                tasks.append(task)
                module_task_keys.append(task_key)
                role_latest_task_key[role] = task_key

            referenced_inside_module: set[str] = set()
            module_task_key_set = set(module_task_keys)
            for task in tasks:
                if task.task_key not in module_task_key_set:
                    continue
                for dependency_key in task.depends_on_task_keys:
                    if dependency_key in module_task_key_set:
                        referenced_inside_module.add(dependency_key)

            module_terminal_keys = [
                task_key
                for task_key in module_task_keys
                if task_key not in referenced_inside_module
            ]
            if not module_terminal_keys and module_task_keys:
                module_terminal_keys = [module_task_keys[-1]]
            terminal_task_keys.extend(module_terminal_keys)

        module_terminal_unique = list(dict.fromkeys(terminal_task_keys))
        global_stage_pairs = [
            ("integration-test", module_terminal_unique),
            ("acceptance", []),
            ("release-manager", []),
        ]
        latest_global_task_key = ""
        for role, preset_depends in global_stage_pairs:
            task_key = f"global:{role}"
            if role == "integration-test":
                depends_on_task_keys = preset_depends
            elif latest_global_task_key:
                depends_on_task_keys = [latest_global_task_key]
            else:
                depends_on_task_keys = []

            level = 0
            for dependency_key in depends_on_task_keys:
                level = max(level, levels.get(dependency_key, 0) + 1)
            levels[task_key] = level

            task = DecomposeBootstrapPreviewTask(
                task_key=task_key,
                phase="global",
                module_key="global",
                role=role,
                objective=f"execute {role} stage for global",
                priority=3,
                depends_on_roles=[],
                depends_on_task_keys=depends_on_task_keys,
                level=level,
            )
            tasks.append(task)
            latest_global_task_key = task_key

        grouped: dict[int, list[str]] = {}
        for task in tasks:
            grouped.setdefault(task.level, []).append(task.task_key)
        parallel_groups = [grouped[level] for level in sorted(grouped.keys())]

        return DecomposeBootstrapPreviewResponse(
            run_id=run_id,
            source=source,
            generated_at=generated_at,
            cache_hit=False,
            cache_fingerprint=fingerprint,
            modules=modules,
            task_count=len(tasks),
            terminal_task_keys=module_terminal_unique
            + ([latest_global_task_key] if latest_global_task_key else []),
            parallel_groups=parallel_groups,
            warnings=warnings,
            tasks=tasks,
        )

    @staticmethod
    def build_decompose_preview_fingerprint(decomposition: dict[str, object]) -> str:
        encoded = json.dumps(
            decomposition,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get_cached_decompose_preview(
        self,
        run: WorkflowRun,
        *,
        fingerprint: str,
    ) -> DecomposeBootstrapPreviewResponse | None:
        cached = run.metadata.get("decompose_bootstrap_preview")
        if not isinstance(cached, dict):
            return None
        cached_fingerprint = str(cached.get("fingerprint", "")).strip()
        if not cached_fingerprint or cached_fingerprint != fingerprint:
            return None

        payload = cached.get("payload")
        if not isinstance(payload, dict):
            return None
        try:
            return DecomposeBootstrapPreviewResponse.model_validate(payload)
        except Exception:
            return None

    def get_preview_snapshot_status(
        self,
        run: WorkflowRun,
        decomposition: dict[str, object],
    ) -> tuple[bool, bool, str | None, str]:
        expected_fingerprint = self.build_decompose_preview_fingerprint(decomposition)
        ready_snapshot = self.get_cached_decompose_preview(
            run,
            fingerprint=expected_fingerprint,
        )
        if ready_snapshot is not None:
            return True, False, ready_snapshot.generated_at, expected_fingerprint

        cached = run.metadata.get("decompose_bootstrap_preview")
        if not isinstance(cached, dict):
            return False, False, None, expected_fingerprint

        cached_fingerprint = str(cached.get("fingerprint", "")).strip()
        payload = cached.get("payload")
        payload_generated_at = (
            self._optional_text_handler(payload.get("generated_at"))
            if isinstance(payload, dict)
            else None
        )
        if cached_fingerprint and cached_fingerprint != expected_fingerprint:
            return False, True, payload_generated_at, expected_fingerprint
        return False, False, payload_generated_at, expected_fingerprint

    @staticmethod
    def persist_decompose_preview(
        run: WorkflowRun,
        *,
        fingerprint: str,
        preview: DecomposeBootstrapPreviewResponse,
    ) -> None:
        run.metadata["decompose_bootstrap_preview"] = {
            "fingerprint": fingerprint,
            "payload": preview.model_dump(),
        }

    @staticmethod
    def extract_module_task_packages_from_decomposition(
        decomposition: dict[str, object],
    ) -> dict[str, list[dict[str, object]]] | None:
        raw_packages = decomposition.get("module_task_packages")
        if not isinstance(raw_packages, dict):
            return None

        normalized_packages: dict[str, list[dict[str, object]]] = {}
        for module_key, tasks in raw_packages.items():
            if not isinstance(module_key, str):
                continue
            if not isinstance(tasks, list):
                continue
            normalized_rows = [item for item in tasks if isinstance(item, dict)]
            if normalized_rows:
                normalized_packages[module_key] = normalized_rows
        return normalized_packages or None

    def get_or_build_decompose_bootstrap_preview(
        self,
        *,
        run_id: str,
        run: WorkflowRun,
        refresh: bool,
    ) -> DecomposeBootstrapPreviewResponse:
        decomposition, source = self.select_decomposition_for_preview(run)
        if decomposition is None:
            raise ValueError("no decomposition data to preview")

        fingerprint = self.build_decompose_preview_fingerprint(decomposition)
        if not refresh:
            cached = self.get_cached_decompose_preview(run, fingerprint=fingerprint)
            if cached is not None:
                return cached.model_copy(
                    update={
                        "cache_hit": True,
                        "cache_fingerprint": fingerprint,
                    }
                )

        preview = self.build_decompose_bootstrap_preview(
            run_id=run_id,
            source=source,
            generated_at=self._now_utc_handler().isoformat(),
            fingerprint=fingerprint,
            decomposition=decomposition,
        )
        self.persist_decompose_preview(
            run,
            fingerprint=fingerprint,
            preview=preview,
        )
        self._persist_run_handler(run_id)
        return preview
