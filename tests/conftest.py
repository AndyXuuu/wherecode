import pytest

import control_center.main as main_module
from control_center.main import store
from control_center.models import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionLayerHealthResponse,
)


class TestActionLayerClient:
    async def get_health(self) -> ActionLayerHealthResponse:
        return ActionLayerHealthResponse(
            status="ok",
            layer="action",
            transport="http",
        )

    async def execute(self, payload: ActionExecuteRequest) -> ActionExecuteResponse:
        lowered = payload.text.lower()
        if "fail" in lowered or "error" in lowered:
            return ActionExecuteResponse(
                status="failed",
                summary="mock execution failed by command content",
                agent="coding",
                trace_id="act_test_fail",
            )
        return ActionExecuteResponse(
            status="success",
            summary="mock execution completed",
            agent="coding",
            trace_id="act_test_success",
        )


@pytest.fixture(autouse=True)
def reset_inmemory_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_module, "action_layer", TestActionLayerClient())
    store.reset()
    yield
    store.reset()
