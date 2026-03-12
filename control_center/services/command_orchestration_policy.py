from __future__ import annotations

import re
import shlex
from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from control_center.models import (
    ActionExecuteResponse,
    Command,
    Task,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowRunOrchestrateRequest,
    WorkflowRunOrchestrateResponse,
    WorkflowRunOrchestrateStrategy,
)
from control_center.services.workflow_scheduler import WorkflowScheduler


class CommandOrchestrationPolicyService:
    CLARIFICATION_MARKERS = (
        "tbd",
        "todo",
        "to-be-determined",
        "to be determined",
        "placeholder",
        "???",
        "待定",
        "待补充",
        "后续补充",
        "不确定",
    )

    def __init__(
        self,
        *,
        enabled: bool,
        prefixes: tuple[str, ...],
        default_max_modules: int,
        default_strategy: str,
        restart_canceled_policy: str,
        workflow_scheduler_provider: Callable[[], WorkflowScheduler],
        now_utc_handler: Callable[[], datetime],
        orchestrate_workflow_run_handler: Callable[
            [str, WorkflowRunOrchestrateRequest],
            Awaitable[WorkflowRunOrchestrateResponse],
        ],
    ) -> None:
        self._enabled = enabled
        self._prefixes = prefixes
        self._default_max_modules = default_max_modules
        self._default_strategy = default_strategy
        self._restart_canceled_policy = self._normalize_restart_canceled_policy(
            restart_canceled_policy
        )
        self._workflow_scheduler_provider = workflow_scheduler_provider
        self._now_utc_handler = now_utc_handler
        self._orchestrate_workflow_run_handler = orchestrate_workflow_run_handler

    @staticmethod
    def _parse_bool_text(value: str) -> bool | None:
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
        return None

    @staticmethod
    def _parse_int_text(value: str, *, minimum: int, maximum: int) -> int | None:
        try:
            parsed = int(value.strip())
        except ValueError:
            return None
        if parsed < minimum or parsed > maximum:
            return None
        return parsed

    def _coerce_orchestrate_strategy(self, value: str | None) -> WorkflowRunOrchestrateStrategy:
        raw = (value or "").strip().lower()
        if not raw:
            raw = self._default_strategy.lower()
        try:
            return WorkflowRunOrchestrateStrategy(raw)
        except ValueError:
            return WorkflowRunOrchestrateStrategy.BALANCED

    @staticmethod
    def _normalize_restart_canceled_policy(value: str) -> str:
        normalized = value.strip().lower().replace("-", "_")
        if normalized in {"always", "on"}:
            return "always"
        if normalized in {"auto", "auto_if_no_requirements"}:
            return "auto_if_no_requirements"
        return "off"

    def _extract_command_orchestrate_intent(
        self,
        command: Command,
    ) -> dict[str, object] | None:
        if not self._enabled:
            return None

        raw_text = command.text.strip()
        if not raw_text:
            return None

        matched_prefix = None
        lowered_text = raw_text.lower()
        for prefix in self._prefixes:
            normalized_prefix = prefix.strip()
            if not normalized_prefix:
                continue
            if lowered_text.startswith(normalized_prefix.lower()):
                matched_prefix = raw_text[: len(normalized_prefix)]
                break
        if matched_prefix is None:
            return None

        payload_text = raw_text[len(matched_prefix) :].strip()
        tokens: list[str]
        try:
            tokens = shlex.split(payload_text) if payload_text else []
        except ValueError:
            tokens = payload_text.split()

        flags: dict[str, str] = {}
        requirements_tokens: list[str] = []
        for token in tokens:
            normalized = token.strip()
            if normalized.startswith("--") and "=" in normalized:
                flag_key, flag_value = normalized[2:].split("=", 1)
                key = flag_key.strip().lower().replace("_", "-")
                value = flag_value.strip()
                if key and value:
                    flags[key] = value
                continue
            requirements_tokens.append(normalized)

        requirements = " ".join(item for item in requirements_tokens if item).strip()
        module_hints_raw = flags.get("module-hints") or flags.get("hints") or ""
        module_hints: list[str] = []
        if module_hints_raw:
            for item in re.split(r"[,\|]", module_hints_raw):
                normalized = item.strip()
                if normalized and normalized not in module_hints:
                    module_hints.append(normalized)

        max_modules = self._parse_int_text(
            flags.get("max-modules", ""),
            minimum=1,
            maximum=20,
        )
        if max_modules is None:
            max_modules = self._default_max_modules

        execute = self._parse_bool_text(flags.get("execute", ""))
        if execute is None:
            execute = True
        force_redecompose = self._parse_bool_text(flags.get("force-redecompose", ""))
        if force_redecompose is None:
            force_redecompose = False
        auto_advance_decompose = self._parse_bool_text(flags.get("auto-advance-decompose", ""))
        if auto_advance_decompose is None:
            auto_advance_decompose = True
        auto_advance_force_refresh_preview = self._parse_bool_text(
            flags.get("auto-advance-force-refresh-preview", "")
        )
        if auto_advance_force_refresh_preview is None:
            auto_advance_force_refresh_preview = False
        restart_latest_canceled_flag_provided = "restart-latest-canceled" in flags
        restart_latest_canceled = self._parse_bool_text(
            flags.get("restart-latest-canceled", "")
        )
        if restart_latest_canceled is None:
            restart_latest_canceled = False
        clarified = self._parse_bool_text(flags.get("clarified", ""))
        if clarified is None:
            clarified = False

        execute_max_loops = self._parse_int_text(
            flags.get("execute-max-loops", ""),
            minimum=1,
            maximum=1000,
        )
        if execute_max_loops is None:
            execute_max_loops = 20

        auto_advance_max_steps = self._parse_int_text(
            flags.get("auto-advance-max-steps", ""),
            minimum=1,
            maximum=100,
        )
        if auto_advance_max_steps is None:
            auto_advance_max_steps = 8

        auto_advance_execute_max_loops = self._parse_int_text(
            flags.get("auto-advance-execute-max-loops", ""),
            minimum=1,
            maximum=1000,
        )

        expected_modules_raw = flags.get("expected-modules", "") or ""
        expected_modules: list[str] = []
        if expected_modules_raw:
            for item in re.split(r"[,\|]", expected_modules_raw):
                normalized = item.strip()
                if normalized and normalized not in expected_modules:
                    expected_modules.append(normalized)

        return {
            "requirements": requirements,
            "module_hints": module_hints,
            "max_modules": max_modules,
            "strategy": self._coerce_orchestrate_strategy(flags.get("strategy")),
            "execute": execute,
            "force_redecompose": force_redecompose,
            "auto_advance_decompose": auto_advance_decompose,
            "auto_advance_max_steps": auto_advance_max_steps,
            "auto_advance_execute_max_loops": auto_advance_execute_max_loops,
            "auto_advance_force_refresh_preview": auto_advance_force_refresh_preview,
            "restart_latest_canceled": restart_latest_canceled,
            "restart_latest_canceled_flag_provided": restart_latest_canceled_flag_provided,
            "execute_max_loops": execute_max_loops,
            "decompose_confirmed_by": flags.get("confirmed-by"),
            "decompose_confirmation_token": flags.get("confirmation-token"),
            "decompose_expected_modules": expected_modules,
            "requested_by": flags.get("requested-by") or command.requested_by,
            "clarified": clarified,
            "source_prefix": matched_prefix.strip(),
        }

    def _detect_clarification_markers(self, requirements: str) -> list[str]:
        lowered = requirements.strip().lower()
        if not lowered:
            return []
        found: list[str] = []
        for marker in self.CLARIFICATION_MARKERS:
            if marker in lowered:
                found.append(marker)
        return sorted(set(found))

    def _create_command_orchestrate_run(
        self,
        *,
        task: Task,
        command: Command,
        requirements: str,
    ) -> WorkflowRun:
        scheduler = self._workflow_scheduler_provider()
        run = scheduler.create_run(
            project_id=task.project_id,
            task_id=task.id,
            requested_by=command.requested_by,
            summary=(requirements[:200] if requirements else None),
        )
        task.metadata["workflow_run_id_latest"] = run.id
        task.metadata["workflow_run_source"] = "command_orchestrate_policy"
        task.metadata["workflow_run_updated_at"] = self._now_utc_handler().isoformat()
        return run

    @staticmethod
    def _extract_latest_workflow_run_id(task: Task) -> str | None:
        latest_run_raw = task.metadata.get("workflow_run_id_latest")
        if isinstance(latest_run_raw, str):
            normalized = latest_run_raw.strip()
            if normalized:
                return normalized
        return None

    def _create_or_restart_command_orchestrate_run(
        self,
        *,
        task: Task,
        command: Command,
        requirements: str,
        restart_latest_canceled: bool,
        requested_by: str | None,
    ) -> tuple[WorkflowRun, str | None]:
        scheduler = self._workflow_scheduler_provider()
        if restart_latest_canceled:
            latest_run_id = self._extract_latest_workflow_run_id(task)
            if latest_run_id:
                try:
                    latest_run = scheduler.get_run(latest_run_id)
                except KeyError:
                    latest_run = None
                if latest_run is not None and latest_run.status == WorkflowRunStatus.CANCELED:
                    restarted_run, _ = scheduler.restart_run(
                        latest_run_id,
                        requested_by=requested_by or command.requested_by,
                        reason="command_orchestrate_policy restart_latest_canceled",
                        copy_decomposition=True,
                    )
                    task.metadata["workflow_run_id_latest"] = restarted_run.id
                    task.metadata["workflow_run_source"] = "command_orchestrate_policy"
                    task.metadata["workflow_run_updated_at"] = (
                        self._now_utc_handler().isoformat()
                    )
                    task.metadata["workflow_run_restart_source"] = latest_run_id
                    task.metadata["workflow_run_restart_applied"] = True
                    return restarted_run, latest_run_id
            task.metadata["workflow_run_restart_applied"] = False

        run = self._create_command_orchestrate_run(
            task=task,
            command=command,
            requirements=requirements,
        )
        return run, None

    def _resolve_restart_latest_canceled(
        self,
        *,
        explicit_flag_provided: bool,
        explicit_flag_value: bool,
        requirements: str,
    ) -> tuple[bool, str]:
        if explicit_flag_provided:
            return explicit_flag_value, "explicit"
        if self._restart_canceled_policy == "always":
            return True, "auto_always"
        if self._restart_canceled_policy == "auto_if_no_requirements":
            if not requirements.strip():
                return True, "auto_if_no_requirements"
            return False, "auto_if_no_requirements_skipped"
        return False, "off"

    def _build_command_orchestrate_state_snapshot(
        self,
        *,
        run: WorkflowRun,
        orchestrate_result: WorkflowRunOrchestrateResponse,
        source_command_id: str,
        restart_source_run_id: str | None = None,
        restart_mode: str | None = None,
        restart_requested: bool | None = None,
    ) -> dict[str, object]:
        decision_machine = (
            orchestrate_result.decision_report.machine
            if orchestrate_result.decision_report is not None
            else None
        )
        run_restart_source = restart_source_run_id
        run_restart_applied = False
        restart_metadata = run.metadata.get("restart")
        if isinstance(restart_metadata, dict):
            source_run = restart_metadata.get("source_run_id")
            if isinstance(source_run, str) and source_run.strip():
                run_restart_source = source_run.strip()
                run_restart_applied = True
        if restart_source_run_id:
            run_restart_applied = True
        return {
            "workflow_run_id": run.id,
            "source_command_id": source_command_id,
            "run_status": orchestrate_result.status_after.run_status,
            "orchestration_status": orchestrate_result.orchestration_status,
            "orchestration_reason": orchestrate_result.reason,
            "strategy": orchestrate_result.strategy.value,
            "actions": orchestrate_result.actions,
            "next_action": orchestrate_result.status_after.next_action,
            "workitem_total": orchestrate_result.status_after.workitem_total,
            "pending_confirmation": orchestrate_result.status_after.has_pending_confirmation,
            "primary_recovery_action": (
                decision_machine.primary_recovery_action
                if decision_machine is not None
                else None
            ),
            "primary_recovery_priority": (
                decision_machine.primary_recovery_priority
                if decision_machine is not None
                else None
            ),
            "primary_recovery_confidence": (
                decision_machine.primary_recovery_confidence
                if decision_machine is not None
                else None
            ),
            "recovery_actions": (
                decision_machine.recovery_actions
                if decision_machine is not None
                else []
            ),
            "restart_source_run_id": run_restart_source,
            "restart_applied": run_restart_applied,
            "restart_mode": restart_mode,
            "restart_requested": restart_requested,
            "updated_at": self._now_utc_handler().isoformat(),
        }

    async def maybe_execute(
        self,
        command: Command,
        task: Task,
    ) -> ActionExecuteResponse | None:
        orchestrate_intent = self._extract_command_orchestrate_intent(command)
        if orchestrate_intent is None:
            return None

        scheduler = self._workflow_scheduler_provider()
        requirements = str(orchestrate_intent.get("requirements", "")).strip()
        restart_latest_canceled, restart_mode = self._resolve_restart_latest_canceled(
            explicit_flag_provided=bool(
                orchestrate_intent.get("restart_latest_canceled_flag_provided", False)
            ),
            explicit_flag_value=bool(
                orchestrate_intent.get("restart_latest_canceled", False)
            ),
            requirements=requirements,
        )
        markers = self._detect_clarification_markers(requirements)
        if markers and not bool(orchestrate_intent.get("clarified", False)):
            command.metadata["command_execution_mode"] = "orchestrate_policy"
            command.metadata["orchestration_status"] = "needs_clarification"
            command.metadata["orchestration_reason"] = (
                "clarification required before orchestration"
            )
            command.metadata["orchestration_next_action"] = "clarify_requirements"
            command.metadata["clarification_required"] = True
            command.metadata["clarification_markers"] = markers
            command.metadata["clarification_hint"] = (
                "resolve ambiguous requirement markers and rerun with --clarified=true"
            )
            task.metadata["workflow_run_source"] = "command_orchestrate_policy"
            task.metadata["workflow_run_status_latest"] = "needs_clarification"
            task.metadata["workflow_run_next_action_latest"] = "clarify_requirements"
            task.metadata["workflow_run_updated_at"] = self._now_utc_handler().isoformat()
            return ActionExecuteResponse(
                status="failed",
                summary=(
                    "clarification required before orchestrate; "
                    f"markers={','.join(markers)}; "
                    "rerun with explicit requirements and --clarified=true"
                ),
                agent="chief-architect",
                trace_id=f"act_orch_clarify_{uuid4().hex[:8]}",
                metadata={
                    "mode": "orchestrate_policy",
                    "orchestration_status": "needs_clarification",
                    "next_action": "clarify_requirements",
                    "clarification_required": True,
                    "clarification_markers": markers,
                    "source_prefix": orchestrate_intent["source_prefix"],
                },
            )

        run, restart_source_run_id = self._create_or_restart_command_orchestrate_run(
            task=task,
            command=command,
            requirements=requirements,
            restart_latest_canceled=restart_latest_canceled,
            requested_by=str(orchestrate_intent.get("requested_by") or "").strip() or None,
        )
        try:
            orchestrate_result = await self._orchestrate_workflow_run_handler(
                run.id,
                WorkflowRunOrchestrateRequest(
                    strategy=orchestrate_intent["strategy"],
                    requirements=(requirements or None),
                    module_hints=orchestrate_intent["module_hints"],
                    max_modules=orchestrate_intent["max_modules"],
                    requested_by=orchestrate_intent["requested_by"],
                    decompose_payload=None,
                    force_redecompose=orchestrate_intent["force_redecompose"],
                    execute=orchestrate_intent["execute"],
                    execute_max_loops=orchestrate_intent["execute_max_loops"],
                    auto_advance_decompose=orchestrate_intent["auto_advance_decompose"],
                    auto_advance_max_steps=orchestrate_intent["auto_advance_max_steps"],
                    auto_advance_execute_max_loops=orchestrate_intent[
                        "auto_advance_execute_max_loops"
                    ],
                    auto_advance_force_refresh_preview=orchestrate_intent[
                        "auto_advance_force_refresh_preview"
                    ],
                    decompose_confirmed_by=orchestrate_intent["decompose_confirmed_by"],
                    decompose_confirmation_token=orchestrate_intent[
                        "decompose_confirmation_token"
                    ],
                    decompose_expected_modules=orchestrate_intent[
                        "decompose_expected_modules"
                    ],
                ),
            )
        except HTTPException as exc:
            state_snapshot = {
                "workflow_run_id": run.id,
                "source_command_id": command.id,
                "run_status": run.status.value,
                "orchestration_status": "failed",
                "orchestration_reason": str(exc.detail),
                "actions": [],
                "next_action": None,
                "primary_recovery_action": None,
                "recovery_actions": [],
                "updated_at": self._now_utc_handler().isoformat(),
            }
            command.metadata["command_execution_mode"] = "orchestrate_policy"
            command.metadata["workflow_run_id"] = run.id
            command.metadata["orchestrate_http_status"] = exc.status_code
            command.metadata["workflow_state_latest"] = state_snapshot
            task.metadata["workflow_state_latest"] = state_snapshot
            task.metadata["workflow_run_id_latest"] = run.id
            task.metadata["workflow_run_source"] = "command_orchestrate_policy"
            task.metadata["workflow_run_updated_at"] = state_snapshot["updated_at"]
            run.metadata["task_workflow_state_latest"] = state_snapshot
            scheduler.persist_run(run.id)
            detail = str(exc.detail)
            return ActionExecuteResponse(
                status="failed",
                summary=f"orchestrate request failed: {detail}",
                agent="chief-architect",
                trace_id=f"act_orch_fail_{uuid4().hex[:8]}",
                metadata={
                    "workflow_run_id": run.id,
                    "orchestrate_http_status": exc.status_code,
                    "reason": detail,
                    "workflow_state_latest": state_snapshot,
                },
            )

        state_snapshot = self._build_command_orchestrate_state_snapshot(
            run=run,
            orchestrate_result=orchestrate_result,
            source_command_id=command.id,
            restart_source_run_id=restart_source_run_id,
            restart_mode=restart_mode,
            restart_requested=restart_latest_canceled,
        )
        command.metadata["command_execution_mode"] = "orchestrate_policy"
        command.metadata["workflow_run_id"] = run.id
        command.metadata["orchestration_status"] = orchestrate_result.orchestration_status
        command.metadata["orchestration_reason"] = orchestrate_result.reason
        command.metadata["orchestration_actions"] = orchestrate_result.actions
        command.metadata["orchestration_strategy"] = orchestrate_result.strategy.value
        command.metadata["orchestration_next_action"] = (
            orchestrate_result.status_after.next_action
        )
        if restart_source_run_id:
            command.metadata["orchestration_restart_source_run_id"] = (
                restart_source_run_id
            )
        command.metadata["orchestration_restart_mode"] = restart_mode
        command.metadata["orchestration_restart_requested"] = restart_latest_canceled
        command.metadata["workflow_state_latest"] = state_snapshot
        decision_machine = (
            orchestrate_result.decision_report.machine
            if orchestrate_result.decision_report is not None
            else None
        )
        if decision_machine is not None:
            command.metadata["orchestration_primary_recovery_action"] = (
                decision_machine.primary_recovery_action
            )

        task.metadata["workflow_run_id_latest"] = run.id
        task.metadata["workflow_run_status_latest"] = orchestrate_result.status_after.run_status
        task.metadata["workflow_run_next_action_latest"] = (
            orchestrate_result.status_after.next_action
        )
        task.metadata["workflow_run_updated_at"] = self._now_utc_handler().isoformat()
        task.metadata["workflow_state_latest"] = state_snapshot
        task.metadata["workflow_run_restart_mode"] = restart_mode
        task.metadata["workflow_run_restart_requested"] = restart_latest_canceled
        if restart_source_run_id:
            task.metadata["workflow_run_restart_source"] = restart_source_run_id
            task.metadata["workflow_run_restart_applied"] = True
        run.metadata["task_workflow_state_latest"] = state_snapshot
        scheduler.persist_run(run.id)

        summary = (
            f"orchestrate status={orchestrate_result.orchestration_status}; "
            f"run_id={run.id}; "
            f"actions={','.join(orchestrate_result.actions) if orchestrate_result.actions else 'none'}; "
            f"next_action={orchestrate_result.status_after.next_action or 'none'}"
        )
        result_status = (
            "failed" if orchestrate_result.orchestration_status == "blocked" else "success"
        )
        return ActionExecuteResponse(
            status=result_status,
            summary=(
                summary
                if result_status == "success"
                else f"{summary}; reason={orchestrate_result.reason or 'blocked'}"
            ),
            agent="chief-architect",
            trace_id=f"act_orch_{uuid4().hex[:8]}",
            metadata={
                "mode": "orchestrate_policy",
                "workflow_run_id": run.id,
                "orchestration_status": orchestrate_result.orchestration_status,
                "orchestration_reason": orchestrate_result.reason,
                "orchestration_actions": orchestrate_result.actions,
                "strategy": orchestrate_result.strategy.value,
                "next_action": orchestrate_result.status_after.next_action,
                "source_prefix": orchestrate_intent["source_prefix"],
                "restart_mode": restart_mode,
                "restart_requested": restart_latest_canceled,
                "workflow_state_latest": state_snapshot,
            },
        )
