from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from control_center.api import (
    create_action_layer_router,
    create_agent_rules_router,
    create_agent_routing_router,
    create_context_memory_router,
    create_hierarchy_router,
    create_metrics_router,
    create_ops_check_router,
    create_runtime_config_router,
    create_workflow_core_router,
    create_workflow_execution_router,
    create_workflow_orchestration_router,
)
from control_center.services.ops_check_runtime import OpsCheckRuntime


def resolve_allowed_origins(raw_value: str | None) -> list[str]:
    raw = raw_value if raw_value is not None else "http://localhost:3000"
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def build_ops_check_runtime(
    *,
    state_store: Any,
    root_dir: Path,
    env_get: Callable[[str, str], str] = os.getenv,
) -> OpsCheckRuntime:
    return OpsCheckRuntime(
        state_store=state_store,
        root_dir=root_dir,
        script_path=Path(
            env_get(
                "WHERECODE_CHECK_LOCAL_SCRIPT",
                str(root_dir / "scripts" / "check_all_local.sh"),
            )
        ),
        log_dir=Path(
            env_get(
                "WHERECODE_CHECK_LOG_DIR",
                str(root_dir / ".wherecode" / "check_runs"),
            )
        ),
        report_dir=Path(
            env_get(
                "WHERECODE_CHECK_REPORT_DIR",
                str(root_dir / "docs" / "v3_reports" / "check_runs"),
            )
        ),
    )


def configure_control_center_middlewares(
    app: FastAPI,
    *,
    allowed_origins: list[str],
    logger: logging.Logger,
    auth_enabled_provider: Callable[[], bool],
    auth_token_provider: Callable[[], str],
    auth_whitelist_prefixes: tuple[str, ...],
    extract_request_token: Callable[[Request], str | None],
) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = f"req_{uuid4().hex[:12]}"
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-Id"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if not auth_enabled_provider():
            return await call_next(request)

        if request.url.path.startswith(auth_whitelist_prefixes):
            return await call_next(request)

        token = extract_request_token(request)
        auth_token = auth_token_provider()
        if not token or token != auth_token:
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})

        return await call_next(request)


def include_control_center_routers(
    app: FastAPI,
    *,
    store_provider: Callable[[], Any],
    command_orchestrate_policy_config_provider: Callable[[], Any],
    context_memory_store_provider: Callable[[], Any],
    agent_rules_registry_provider: Callable[[], Any],
    workflow_scheduler_provider: Callable[[], Any],
    workflow_engine_provider: Callable[[], Any],
    metrics_alert_policy_store_provider: Callable[[], Any],
    authorize_metrics_policy_update: Callable[..., Any],
    authorize_metrics_rollback_approval: Callable[..., Any],
    metrics_rollback_requires_approval_provider: Callable[[], bool],
    agent_router_provider: Callable[[], Any],
    action_layer_health_handler: Callable[[], Any],
    action_layer_execute_handler: Callable[..., Any],
    execute_workflow_run_handler: Callable[..., Any],
    interrupt_workflow_run_handler: Callable[..., Any],
    decompose_bootstrap_handler: Callable[..., Any],
    decompose_pending_handler: Callable[..., Any],
    decompose_status_handler: Callable[..., Any],
    routing_decisions_handler: Callable[..., Any],
    decompose_preview_handler: Callable[..., Any],
    decompose_advance_handler: Callable[..., Any],
    decompose_advance_loop_handler: Callable[..., Any],
    decompose_confirm_handler: Callable[..., Any],
    orchestrate_handler: Callable[..., Any],
    orchestrate_latest_handler: Callable[..., Any],
    orchestrate_recover_handler: Callable[..., Any],
    ops_check_runtime: OpsCheckRuntime,
) -> None:
    app.include_router(
        create_runtime_config_router(
            command_orchestrate_policy_config_provider=(
                command_orchestrate_policy_config_provider
            ),
        )
    )
    app.include_router(
        create_agent_rules_router(
            agent_rules_registry_provider=agent_rules_registry_provider,
        )
    )
    app.include_router(
        create_context_memory_router(
            context_memory_store_provider=context_memory_store_provider,
        )
    )
    app.include_router(
        create_workflow_core_router(
            workflow_scheduler_provider=workflow_scheduler_provider,
            workflow_engine_provider=workflow_engine_provider,
        )
    )
    app.include_router(
        create_workflow_execution_router(
            execute_workflow_run_handler=execute_workflow_run_handler,
            interrupt_workflow_run_handler=interrupt_workflow_run_handler,
            workflow_scheduler_provider=workflow_scheduler_provider,
        )
    )
    app.include_router(
        create_hierarchy_router(
            store_provider=store_provider,
        )
    )
    app.include_router(
        create_metrics_router(
            store_provider=store_provider,
            workflow_scheduler_provider=workflow_scheduler_provider,
            metrics_alert_policy_store_provider=metrics_alert_policy_store_provider,
            authorize_metrics_policy_update=authorize_metrics_policy_update,
            authorize_metrics_rollback_approval=authorize_metrics_rollback_approval,
            metrics_rollback_requires_approval_provider=(
                metrics_rollback_requires_approval_provider
            ),
        )
    )
    app.include_router(
        create_agent_routing_router(
            agent_router_provider=agent_router_provider,
        )
    )
    app.include_router(
        create_action_layer_router(
            action_layer_health_handler=action_layer_health_handler,
            action_layer_execute_handler=action_layer_execute_handler,
        )
    )
    app.include_router(
        create_workflow_orchestration_router(
            decompose_bootstrap_handler=decompose_bootstrap_handler,
            decompose_pending_handler=decompose_pending_handler,
            decompose_status_handler=decompose_status_handler,
            routing_decisions_handler=routing_decisions_handler,
            decompose_preview_handler=decompose_preview_handler,
            decompose_advance_handler=decompose_advance_handler,
            decompose_advance_loop_handler=decompose_advance_loop_handler,
            decompose_confirm_handler=decompose_confirm_handler,
            orchestrate_handler=orchestrate_handler,
            orchestrate_latest_handler=orchestrate_latest_handler,
            orchestrate_recover_handler=orchestrate_recover_handler,
        )
    )
    app.include_router(create_ops_check_router(ops_check_runtime=ops_check_runtime))
