from control_center.models import WorkItem
from control_center.services import Gatekeeper


def test_doc_gate_fail_once_rule() -> None:
    gatekeeper = Gatekeeper()
    item = WorkItem(
        workflow_run_id="wfr_alpha",
        role="doc-manager",
        module_key="doc-reflow-once",
    )
    decision = gatekeeper.evaluate(item)
    assert decision is not None
    assert decision.gate_type == "doc"
    assert not decision.passed

    item.metadata["reflow_attempt"] = 1
    decision_retry = gatekeeper.evaluate(item)
    assert decision_retry is not None
    assert decision_retry.passed


def test_security_gate_risk_marker() -> None:
    gatekeeper = Gatekeeper()
    item = WorkItem(
        workflow_run_id="wfr_alpha",
        role="security-review",
        module_key="auth-risk",
    )
    decision = gatekeeper.evaluate(item)
    assert decision is not None
    assert decision.gate_type == "security"
    assert not decision.passed
