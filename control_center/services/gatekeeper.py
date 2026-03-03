from __future__ import annotations

from dataclasses import dataclass

from control_center.models import GateType, WorkItem
from control_center.services.gates import DocGate, SecurityGate, TestGate


@dataclass(frozen=True, slots=True)
class GateDecision:
    gate_type: GateType
    passed: bool
    summary: str
    executed_by: str


class Gatekeeper:
    def __init__(self) -> None:
        self._doc_gate = DocGate()
        self._test_gate = TestGate()
        self._security_gate = SecurityGate()

    def evaluate(self, workitem: WorkItem) -> GateDecision | None:
        role = workitem.role
        if role == "doc-manager":
            result = self._doc_gate.evaluate(workitem)
            return GateDecision(
                gate_type=GateType.DOC,
                passed=result.passed,
                summary=result.summary,
                executed_by="doc-gate",
            )
        if role in {"qa-test", "integration-test"}:
            result = self._test_gate.evaluate(workitem)
            return GateDecision(
                gate_type=GateType.TEST,
                passed=result.passed,
                summary=result.summary,
                executed_by="test-gate",
            )
        if role == "security-review":
            result = self._security_gate.evaluate(workitem)
            return GateDecision(
                gate_type=GateType.SECURITY,
                passed=result.passed,
                summary=result.summary,
                executed_by="security-gate",
            )
        return None
