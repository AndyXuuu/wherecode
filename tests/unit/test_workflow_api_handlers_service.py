from __future__ import annotations

import asyncio

from control_center.services.workflow_api_handlers import WorkflowAPIHandlersService


class _FakeDecomposeRuntime:
    async def decompose_bootstrap_workflow_run(self, run_id: str, payload):
        return {"op": "decompose_bootstrap", "run_id": run_id, "payload": payload}

    async def get_decompose_bootstrap_pending(self, run_id: str):
        return {"op": "decompose_pending", "run_id": run_id}

    async def get_decompose_bootstrap_aggregate_status(self, run_id: str):
        return {"op": "decompose_status", "run_id": run_id}

    async def get_workflow_run_routing_decisions(self, run_id: str):
        return {"op": "routing_decisions", "run_id": run_id}

    async def get_decompose_bootstrap_preview(self, run_id: str, refresh: bool = False):
        return {"op": "decompose_preview", "run_id": run_id, "refresh": refresh}

    async def advance_decompose_bootstrap_run(self, run_id: str, payload):
        return {"op": "decompose_advance", "run_id": run_id, "payload": payload}

    async def advance_decompose_bootstrap_run_loop(self, run_id: str, payload):
        return {"op": "decompose_advance_loop", "run_id": run_id, "payload": payload}

    async def confirm_decompose_bootstrap_workflow_run(self, run_id: str, payload):
        return {"op": "decompose_confirm", "run_id": run_id, "payload": payload}


class _FakeOrchestrationRuntime:
    def __init__(self, label: str) -> None:
        self.label = label

    async def orchestrate_workflow_run(self, run_id: str, payload):
        return {"op": "orchestrate", "run_id": run_id, "payload": payload, "label": self.label}

    async def get_latest_orchestrate_telemetry(self, run_id: str):
        return {"op": "orchestrate_latest", "run_id": run_id, "label": self.label}

    async def execute_orchestrate_recovery_action(self, run_id: str, payload):
        return {
            "op": "orchestrate_recover",
            "run_id": run_id,
            "payload": payload,
            "label": self.label,
        }


class _FakeExecutionRuntime:
    async def execute_workflow_run(self, run_id: str, payload):
        return {"op": "execute_workflow", "run_id": run_id, "payload": payload}

    async def interrupt_workflow_run(self, run_id: str, payload):
        return {"op": "interrupt_workflow", "run_id": run_id, "payload": payload}


def test_workflow_api_handlers_decompose_delegation() -> None:
    service = WorkflowAPIHandlersService(
        workflow_decompose_runtime_service_provider=lambda: _FakeDecomposeRuntime(),
        workflow_orchestration_runtime_service_provider=lambda: _FakeOrchestrationRuntime(
            "A"
        ),
        workflow_execution_runtime_service_provider=lambda: _FakeExecutionRuntime(),
    )

    payload = {"requirements": "test"}
    result = asyncio.run(service.decompose_bootstrap_workflow_run("run-1", payload))
    assert result["op"] == "decompose_bootstrap"
    assert result["run_id"] == "run-1"
    assert result["payload"] == payload


def test_workflow_api_handlers_orchestration_uses_dynamic_provider() -> None:
    holder: dict[str, _FakeOrchestrationRuntime] = {"svc": _FakeOrchestrationRuntime("A")}
    service = WorkflowAPIHandlersService(
        workflow_decompose_runtime_service_provider=lambda: _FakeDecomposeRuntime(),
        workflow_orchestration_runtime_service_provider=lambda: holder["svc"],
        workflow_execution_runtime_service_provider=lambda: _FakeExecutionRuntime(),
    )

    first = asyncio.run(service.get_latest_orchestrate_telemetry("run-1"))
    assert first["label"] == "A"

    holder["svc"] = _FakeOrchestrationRuntime("B")
    second = asyncio.run(service.get_latest_orchestrate_telemetry("run-1"))
    assert second["label"] == "B"


def test_workflow_api_handlers_execute_delegation() -> None:
    service = WorkflowAPIHandlersService(
        workflow_decompose_runtime_service_provider=lambda: _FakeDecomposeRuntime(),
        workflow_orchestration_runtime_service_provider=lambda: _FakeOrchestrationRuntime(
            "A"
        ),
        workflow_execution_runtime_service_provider=lambda: _FakeExecutionRuntime(),
    )

    payload = {"requested_by": "test"}
    result = asyncio.run(service.execute_workflow_run("run-2", payload))
    assert result["op"] == "execute_workflow"
    assert result["run_id"] == "run-2"
    assert result["payload"] == payload


def test_workflow_api_handlers_interrupt_delegation() -> None:
    service = WorkflowAPIHandlersService(
        workflow_decompose_runtime_service_provider=lambda: _FakeDecomposeRuntime(),
        workflow_orchestration_runtime_service_provider=lambda: _FakeOrchestrationRuntime(
            "A"
        ),
        workflow_execution_runtime_service_provider=lambda: _FakeExecutionRuntime(),
    )

    payload = {"requested_by": "owner", "reason": "manual stop"}
    result = asyncio.run(service.interrupt_workflow_run("run-3", payload))
    assert result["op"] == "interrupt_workflow"
    assert result["run_id"] == "run-3"
    assert result["payload"] == payload
