from __future__ import annotations

import asyncio
import json

from control_center.executors.service import ExecutorService
from control_center.models import ActionExecuteResponse, WorkItem, WorkflowRun


async def _ok_action_executor(request):
    return ActionExecuteResponse(
        status="success",
        summary=f"ok:{request.role}:{request.module_key}",
        agent=request.agent or "module-dev",
        trace_id="act_exec_service_ok",
    )


def test_executor_service_routes_strategy_from_policy(tmp_path) -> None:
    policy_path = tmp_path / "role_routing.v3.json"
    policy_path.write_text(
        json.dumps(
            {
                "version": "v3",
                "default_executor": "opencode",
                "default_strategy": "native",
                "roles": {
                    "doc-manager": {
                        "executor": "opencode",
                        "strategy": "ohmy",
                        "category": "docs",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service = ExecutorService(
        role_routing_policy_file=str(policy_path),
        action_executor=_ok_action_executor,
    )
    run = WorkflowRun(project_id="proj_exec")
    item = WorkItem(
        workflow_run_id=run.id,
        role="doc-manager",
        module_key="docs",
    )

    result = asyncio.run(
        service.execute_workitem(
            run=run,
            workitem=item,
            text="update docs",
        )
    )
    assert result.status == "success"
    assert result.trace_id == "act_exec_service_ok"
    assert result.error is None
