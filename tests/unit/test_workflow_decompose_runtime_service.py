from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from control_center.models import (
    ActionExecuteResponse,
    ConfirmDecomposeBootstrapWorkflowRequest,
    DecomposeBootstrapAggregateStatusResponse,
    DecomposeBootstrapPreviewResponse,
    DecomposeBootstrapWorkflowRequest,
)
from control_center.services import WorkflowDecomposeRuntimeService, WorkflowScheduler


class _FakeBootstrapResult:
    def __init__(self) -> None:
        self.workitems = []


class _FakeEngine:
    def bootstrap_standard_pipeline(
        self,
        run_id: str,
        modules: list[str],
        module_task_packages: dict[str, list[dict[str, object]]] | None = None,
    ) -> _FakeBootstrapResult:
        _ = (run_id, modules, module_task_packages)
        return _FakeBootstrapResult()

    async def execute_until_blocked(self, *, run_id: str, max_loops: int):  # pragma: no cover
        _ = (run_id, max_loops)
        raise AssertionError("execute_until_blocked should not be called in this test")


def _build_service(
    scheduler: WorkflowScheduler,
    *,
    chief_result: ActionExecuteResponse | None = None,
    allow_fallback: bool = True,
    require_confirmation: bool = True,
) -> WorkflowDecomposeRuntimeService:
    engine = _FakeEngine()
    chief_reply = chief_result or ActionExecuteResponse(
        status="success",
        summary="ok",
        agent="chief-architect",
        trace_id="act_test_ok",
        metadata={"modules": ["alpha"]},
    )

    async def _execute_chief(_request) -> ActionExecuteResponse:
        return chief_reply

    return WorkflowDecomposeRuntimeService(
        workflow_scheduler_provider=lambda: scheduler,
        workflow_engine_provider=lambda: engine,
        now_utc_handler=lambda: datetime.now(timezone.utc),
        optional_text_handler=lambda value: str(value).strip() if value is not None else None,
        get_pending_decomposition_handler=lambda run: (
            run.metadata.get("pending_decomposition")
            if isinstance(run.metadata.get("pending_decomposition"), dict)
            else None
        ),
        get_pending_confirmation_status_handler=lambda pending: str(
            pending.get("confirmation", {}).get("status", "")
        ).strip().lower(),
        normalize_module_candidates_handler=lambda values: [
            str(item).strip() for item in values if str(item).strip()
        ],
        get_preview_snapshot_status_handler=lambda _run, _decomposition: (
            False,
            False,
            None,
            None,
        ),
        build_decompose_aggregate_status_handler=lambda run_id, run: DecomposeBootstrapAggregateStatusResponse(
            run_id=run_id,
            run_status=run.status,
        ),
        build_routing_decisions_response_handler=lambda run_id, _run: {
            "run_id": run_id,
            "source": "none",
            "has_routing_decisions": False,
            "module_count": 0,
            "decisions": [],
        },
        get_or_build_decompose_bootstrap_preview_handler=lambda run_id, _run, _refresh: (
            DecomposeBootstrapPreviewResponse(run_id=run_id, source="test")
        ),
        select_decomposition_for_preview_handler=lambda _run: (None, "none"),
        extract_preview_modules_handler=lambda _decomposition: [],
        extract_module_task_packages_from_decomposition_handler=lambda _decomposition: None,
        build_chief_decompose_prompt_handler=(
            lambda requirements, max_modules, module_hints, project_id, task_id: (
                f"req={requirements}; max={max_modules}; hints={module_hints}; "
                f"project={project_id}; task={task_id}"
            )
        ),
        execute_chief_action_handler=_execute_chief,
        build_synthetic_decomposition_fallback_handler=lambda _requirements, _module_hints, _max_modules: {
            "modules": ["fallback"],
            "required_tags": ["tag-fallback"],
            "requirement_module_map": {"tag-fallback": ["fallback"]},
            "module_task_packages": {"fallback": [{"role": "module-dev", "objective": "do"}]},
        },
        extract_modules_from_chief_response_handler=lambda _response, _max_modules: ["alpha"],
        validate_decomposition_coverage_handler=lambda _requirements, _module_hints, _modules, _chief_metadata: (
            ["tag-alpha"],
            [],
        ),
        validate_requirement_module_mapping_handler=lambda _required_tags, modules, _chief_metadata: (
            {"tag-alpha": modules},
            [],
            {},
            True,
        ),
        validate_module_task_packages_handler=lambda modules, _chief_metadata: (
            {module: [{"role": "module-dev", "objective": f"build {module}"}] for module in modules},
            [],
            {},
            {},
            True,
        ),
        dev_routing_apply_handler=lambda _modules, module_task_packages, _chief_metadata: (
            module_task_packages,
            {},
        ),
        decompose_allow_synthetic_fallback_provider=lambda: allow_fallback,
        decompose_require_explicit_map_provider=lambda: True,
        decompose_require_task_package_provider=lambda: True,
        decompose_require_confirmation_provider=lambda: require_confirmation,
    )


def test_decompose_runtime_bootstrap_requires_chief_success_when_fallback_disabled() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj", requested_by="owner")
    service = _build_service(
        scheduler,
        chief_result=ActionExecuteResponse(
            status="failed",
            summary="provider timeout",
            agent="chief-architect",
            trace_id="act_fail",
        ),
        allow_fallback=False,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.decompose_bootstrap_workflow_run(
                run.id,
                DecomposeBootstrapWorkflowRequest(requirements="build platform"),
            )
        )
    assert exc.value.status_code == 422
    assert "chief decomposition failed" in str(exc.value.detail)


def test_decompose_runtime_bootstrap_writes_pending_confirmation() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj", requested_by="owner")
    service = _build_service(scheduler, require_confirmation=True)

    response = asyncio.run(
        service.decompose_bootstrap_workflow_run(
            run.id,
            DecomposeBootstrapWorkflowRequest(requirements="build platform"),
        )
    )

    assert response.confirmation_required is True
    assert response.confirmation_status == "pending"
    updated = scheduler.get_run(run.id)
    assert "pending_decomposition" in updated.metadata


def test_decompose_runtime_confirm_approved_clears_pending() -> None:
    scheduler = WorkflowScheduler()
    run = scheduler.create_run(project_id="proj", requested_by="owner")
    run.metadata["pending_decomposition"] = {
        "modules": ["alpha"],
        "module_task_packages": {"alpha": [{"role": "module-dev", "objective": "build alpha"}]},
        "confirmation": {
            "status": "pending",
            "token": "tok-1",
        },
    }

    service = _build_service(scheduler)
    response = asyncio.run(
        service.confirm_decompose_bootstrap_workflow_run(
            run.id,
            ConfirmDecomposeBootstrapWorkflowRequest(
                confirmed_by="owner",
                approved=True,
                confirmation_token="tok-1",
            ),
        )
    )

    assert response.confirmation_status == "approved"
    updated = scheduler.get_run(run.id)
    assert "pending_decomposition" not in updated.metadata
    assert "chief_decomposition" in updated.metadata
