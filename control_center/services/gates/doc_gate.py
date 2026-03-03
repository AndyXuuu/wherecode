from __future__ import annotations

from control_center.models import WorkItem
from control_center.services.gates.types import GateEvalResult


class DocGate:
    def evaluate(self, workitem: WorkItem) -> GateEvalResult:
        module = (workitem.module_key or "").lower()
        reflow_attempt = int(workitem.metadata.get("reflow_attempt", 0))

        if "doc-reflow-once" in module and reflow_attempt == 0:
            return GateEvalResult(
                passed=False,
                summary="doc gate failed on first attempt; requires reflow",
            )
        if "doc-fail" in module and "doc-reflow-once" not in module:
            return GateEvalResult(
                passed=False,
                summary="doc gate failed by module marker",
            )
        return GateEvalResult(
            passed=True,
            summary="doc gate passed",
        )
