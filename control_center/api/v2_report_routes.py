from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from control_center.models import (
    V2ReportActionSuggestion,
    V2ReportCompactSummary,
    V2ReportFailureTaxonomy,
    V2ReportSummaryResponse,
)


def create_v2_report_router(*, root_dir: Path | None = None) -> APIRouter:
    router = APIRouter()
    resolved_root_dir = (
        root_dir.resolve()
        if root_dir is not None
        else Path(__file__).resolve().parents[2]
    )

    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _resolve_input_path(raw: str) -> Path:
        candidate = Path(raw)
        if candidate.is_absolute():
            return candidate.resolve()
        return (resolved_root_dir / candidate).resolve()

    def _resolve_report_payload(target: Path) -> tuple[Path, dict[str, Any], Path | None]:
        payload = _read_json(target)
        report_path_value = str(payload.get("report_path") or "").strip()
        if report_path_value:
            report_candidate = Path(report_path_value)
            if not report_candidate.is_absolute():
                report_candidate = (target.parent / report_candidate).resolve()
            if report_candidate.exists():
                return report_candidate, _read_json(report_candidate), target
        return target, payload, None

    def _resolve_report_by_run_id(target_run_id: str) -> tuple[Path, dict[str, Any], Path | None]:
        reports_dir = (resolved_root_dir / "docs" / "v2_reports").resolve()
        if not reports_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"v2 report directory not found: {reports_dir}",
            )

        candidates = sorted(
            reports_dir.glob("*-v2-run.json"),
            key=lambda item: item.name,
            reverse=True,
        )
        for candidate in candidates:
            try:
                report_file, payload, latest_pointer = _resolve_report_payload(candidate)
            except Exception:  # noqa: BLE001
                continue
            outputs = payload.get("outputs") or {}
            run = payload.get("run") or {}
            workflow_run_id = str(
                outputs.get("workflow_run_id") or run.get("workflow_run_id") or ""
            ).strip()
            if workflow_run_id and workflow_run_id == target_run_id:
                return report_file, payload, latest_pointer

        raise HTTPException(
            status_code=404,
            detail=f"v2 report not found for run_id: {target_run_id}",
        )

    def _resolve_report_by_report_id(
        target_report_id: str,
    ) -> tuple[Path, dict[str, Any], Path | None]:
        reports_dir = (resolved_root_dir / "docs" / "v2_reports").resolve()
        if not reports_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"v2 report directory not found: {reports_dir}",
            )
        candidate = (reports_dir / f"{target_report_id}.json").resolve()
        if not candidate.exists():
            raise HTTPException(
                status_code=404,
                detail=f"v2 report not found for report_id: {target_report_id}",
            )
        try:
            return _resolve_report_payload(candidate)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=422,
                detail=f"invalid v2 report payload: {exc}",
            ) from exc

    def _resolve_risk_level(final_status: str, severity: str) -> str:
        status = final_status.strip().lower()
        sev = severity.strip().lower()
        if status in {"success", "succeeded"}:
            return "low"
        if sev in {"critical", "high"}:
            return "high"
        if status in {"failed", "error"}:
            return "high"
        if status == "canceled":
            return "medium"
        if sev == "medium":
            return "medium"
        return "low"

    def _classify_action_type(command: str) -> str:
        lowered = command.lower()
        if "v2-replay" in lowered or "v2-run" in lowered:
            return "rerun"
        if "check_all" in lowered or "v2_gate" in lowered:
            return "validate"
        if "orchestrate-policy" in lowered:
            return "dependency-check"
        return "other"

    def _resolve_runbook_ref(action_type: str) -> str:
        if action_type == "rerun":
            return "ops://v2-replay"
        if action_type == "validate":
            return "ops://check-all-v2"
        if action_type == "dependency-check":
            return "ops://orchestrate-policy"
        return "ops://manual-review"

    def _resolve_estimated_cost(action_type: str) -> str:
        if action_type in {"validate", "dependency-check"}:
            return "low"
        if action_type == "rerun":
            return "medium"
        return "high"

    def _resolve_alert_priority(
        *,
        final_status: str,
        severity: str,
        action_required: bool,
    ) -> str:
        status = final_status.strip().lower()
        sev = severity.strip().lower()
        if status in {"failed", "error"} and sev in {"critical"}:
            return "P0"
        if status in {"failed", "error"} and sev in {"high", "critical"}:
            return "P1"
        if status in {"failed", "error", "canceled"} or sev == "medium":
            return "P2"
        if action_required:
            return "P2"
        return "P3"

    def _resolve_decision(action_required: bool, alert_priority: str) -> str:
        if not action_required:
            return "observe"
        if alert_priority in {"P0", "P1"}:
            return "act_now"
        return "review_and_run"

    def _action_base_score(alert_priority: str) -> int:
        if alert_priority == "P0":
            return 100
        if alert_priority == "P1":
            return 85
        if alert_priority == "P2":
            return 65
        return 40

    @router.get("/reports/v2/summary", response_model=V2ReportSummaryResponse)
    def get_v2_report_summary(
        subproject: str = "stock-sentiment",
        run_id: str | None = None,
        report_id: str | None = None,
        report_path: str | None = None,
        latest_path: str | None = None,
        compact: bool = False,
        max_actions: int = 3,
        min_score: int = 0,
        action_type: str | None = None,
    ) -> V2ReportSummaryResponse:
        if report_id and report_id.strip():
            target_report_id = report_id.strip()
            source_input = (
                resolved_root_dir / "docs" / "v2_reports" / f"latest_{subproject}_v2_run.json"
            ).resolve()
            report_file, payload, latest_pointer = _resolve_report_by_report_id(target_report_id)
        elif run_id and run_id.strip():
            target_run_id = run_id.strip()
            source_input = (
                resolved_root_dir / "docs" / "v2_reports" / f"latest_{subproject}_v2_run.json"
            ).resolve()
            try:
                report_file, payload, latest_pointer = _resolve_report_by_run_id(target_run_id)
            except HTTPException:
                raise
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=422,
                    detail=f"invalid v2 report payload: {exc}",
                ) from exc
        else:
            if report_path:
                source_input = _resolve_input_path(report_path)
            elif latest_path:
                source_input = _resolve_input_path(latest_path)
            else:
                source_input = (
                    resolved_root_dir / "docs" / "v2_reports" / f"latest_{subproject}_v2_run.json"
                ).resolve()

            if not source_input.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"v2 report input not found: {source_input}",
                )

            try:
                report_file, payload, latest_pointer = _resolve_report_payload(source_input)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=422,
                    detail=f"invalid v2 report payload: {exc}",
                ) from exc

        run = payload.get("run") or {}
        diagnosis = payload.get("diagnosis") or {}
        taxonomy = diagnosis.get("failure_taxonomy") or {}
        retry_hints = [
            str(item).strip()
            for item in (diagnosis.get("retry_hints") or [])
            if str(item).strip()
        ]
        next_commands = [
            str(item).strip()
            for item in (diagnosis.get("next_commands") or [])
            if str(item).strip()
        ]
        final_status = str(run.get("final_status") or "")
        taxonomy_code = str(taxonomy.get("code") or "")
        taxonomy_severity = str(taxonomy.get("severity") or "")
        taxonomy_reason = str(taxonomy.get("reason") or "")
        risk_level = _resolve_risk_level(final_status=final_status, severity=taxonomy_severity)
        action_required = final_status.strip().lower() not in {"success", "succeeded"}
        alert_priority = _resolve_alert_priority(
            final_status=final_status,
            severity=taxonomy_severity,
            action_required=action_required,
        )
        decision = _resolve_decision(action_required=action_required, alert_priority=alert_priority)
        base_score = _action_base_score(alert_priority)

        if compact:
            bounded_max_actions = max(1, min(max_actions, 5))
        else:
            bounded_max_actions = max(1, min(max_actions, 10))
        bounded_min_score = max(0, min(min_score, 100))
        action_type_filters = {
            value.strip().lower()
            for value in str(action_type or "").split(",")
            if value.strip()
        }

        suggested_actions: list[V2ReportActionSuggestion] = []
        for index, command in enumerate(next_commands, start=1):
            reason = (
                retry_hints[index - 1]
                if index - 1 < len(retry_hints)
                else (taxonomy_reason or "recommended follow-up action")
            )
            action_kind = _classify_action_type(command)
            action_digest = hashlib.sha1(command.encode("utf-8")).hexdigest()[:8]
            score = max(0, base_score - (index - 1) * 7)
            can_auto_execute = action_kind in {"validate", "dependency-check"} or (
                action_kind == "rerun" and alert_priority in {"P2", "P3"}
            )
            requires_confirmation = alert_priority in {"P0", "P1"} or not can_auto_execute
            suggested_actions.append(
                V2ReportActionSuggestion(
                    priority=index,
                    action_id=f"{action_kind}:{action_digest}",
                    action_type=action_kind,
                    command=command,
                    reason=reason,
                    score=score,
                    runbook_ref=_resolve_runbook_ref(action_kind),
                    can_auto_execute=can_auto_execute,
                    requires_confirmation=requires_confirmation,
                    estimated_cost=_resolve_estimated_cost(action_kind),
                )
            )

        filtered_actions = [
            item
            for item in suggested_actions
            if item.score >= bounded_min_score
            and (not action_type_filters or item.action_type in action_type_filters)
        ]
        prioritized_actions = filtered_actions[:bounded_max_actions]
        for index, item in enumerate(prioritized_actions, start=1):
            item.priority = index

        status_line = (
            f"{str(run.get('subproject_key') or '').strip() or 'subproject'} "
            f"{str(run.get('mode') or '').strip() or 'run'} "
            f"{final_status.strip() or 'unknown'} "
            f"[{taxonomy_code.strip() or 'unknown'}]"
        ).strip()
        primary_action = prioritized_actions[0] if prioritized_actions else None
        compact_summary = V2ReportCompactSummary(
            status_line=status_line,
            action_required=action_required,
            alert_priority=alert_priority,
            decision=decision,
            risk_level=risk_level,
            primary_action_id=primary_action.action_id if primary_action else "",
            top_retry_hint=(
                primary_action.reason
                if primary_action is not None
                else (retry_hints[0] if retry_hints else "")
            ),
            top_next_command=(
                primary_action.command
                if primary_action is not None
                else (next_commands[0] if next_commands else "")
            ),
        )

        return V2ReportSummaryResponse(
            source_input=str(source_input),
            latest_pointer=str(latest_pointer) if latest_pointer else "",
            report_path=str(report_file),
            report_id=report_file.stem,
            captured_at=str(payload.get("captured_at") or ""),
            subproject_key=str(run.get("subproject_key") or ""),
            mode=str(run.get("mode") or ""),
            final_status=final_status,
            failure_taxonomy=V2ReportFailureTaxonomy(
                code=taxonomy_code,
                stage=str(taxonomy.get("stage") or ""),
                severity=taxonomy_severity,
                reason=taxonomy_reason,
            ),
            compact=compact_summary,
            prioritized_actions=prioritized_actions,
            primary_action=primary_action,
            retry_hints=retry_hints,
            next_commands=next_commands,
        )

    return router
