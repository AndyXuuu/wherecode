from __future__ import annotations

from control_center.models import WorkItem
from control_center.services.gates.types import GateEvalResult


class SecurityGate:
    def evaluate(self, workitem: WorkItem) -> GateEvalResult:
        module = (workitem.module_key or "").lower()
        if "security-fail" in module or "risk" in module:
            return GateEvalResult(
                passed=False,
                summary="security gate failed by risk marker",
            )
        return GateEvalResult(
            passed=True,
            summary="security gate passed",
        )
