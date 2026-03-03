from __future__ import annotations

from control_center.models import WorkItem
from control_center.services.gates.types import GateEvalResult


class TestGate:
    def evaluate(self, workitem: WorkItem) -> GateEvalResult:
        module = (workitem.module_key or "").lower()
        if "test-fail" in module:
            return GateEvalResult(
                passed=False,
                summary="test gate failed by module marker",
            )
        return GateEvalResult(
            passed=True,
            summary="test gate passed",
        )
