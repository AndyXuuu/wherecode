from __future__ import annotations

import json
from pathlib import Path


def test_react_protocol_schema_exists_and_has_required_contract() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "control_center"
        / "capabilities"
        / "protocols"
        / "react_trace_v1.schema.json"
    )
    assert schema_path.exists()

    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    assert payload["$id"] == "wherecode://protocols/react_trace/v1"
    assert payload["title"] == "WhereCode ReAct Trace Protocol v1"

    required = set(payload["required"])
    assert {"standard", "version", "loop_state", "steps", "final_decision", "truncated"} <= required

    metadata_def = payload["$defs"]["AgentStandardMetadata"]
    metadata_required = set(metadata_def["required"])
    assert {"protocol", "version", "trace_schema"} <= metadata_required
