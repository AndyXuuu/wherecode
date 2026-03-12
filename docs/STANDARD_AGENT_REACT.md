# Standard Agent ReAct Protocol (V1)

Updated: 2026-03-11

## Scope

This protocol defines the normalized execution trace returned by Action Layer:
- response field: `ActionExecuteResponse.agent_trace`
- response metadata: `ActionExecuteResponse.metadata.agent_standard`

It is used for:
- unified agent interoperability
- remote/mobile progress visualization
- deterministic audit/replay of execution decisions

## Normative Schema

- Schema ID: `wherecode://protocols/react_trace/v1`
- Schema file: `control_center/capabilities/protocols/react_trace_v1.schema.json`

## Contract

### `metadata.agent_standard`

Required keys:
- `protocol`: `ReAct`
- `version`: `1.0`
- `trace_schema`: `wherecode://protocols/react_trace/v1`

Optional key:
- `trace_schema_path`: local schema path

### `agent_trace`

Required keys:
- `standard`: `ReAct`
- `version`: `1.0`
- `loop_state`: `planning|acting|observing|needs_discussion|final`
- `steps`: ordered step list, max 12
- `final_decision`: `success|failed|needs_discussion`
- `truncated`: `bool`

`steps[]` item shape:
- `index`: int >= 1
- `phase`: `plan|act|observe|final`
- `content`: concise operational trace text
- `tool`: optional tool name
- `status`: optional `ok|error|needs_discussion|skipped`

## Runtime Rules

- If upstream model returns `agent_trace`, Action Layer sanitizes it to protocol enums and bounds.
- If upstream model does not return `agent_trace`, Action Layer synthesizes a default ReAct trace.
- `steps[].content` is an operational summary, not chain-of-thought.

## Minimal Example

```json
{
  "status": "success",
  "summary": "execution completed",
  "agent": "coding-agent",
  "trace_id": "act_xxx",
  "metadata": {
    "agent_standard": {
      "protocol": "ReAct",
      "version": "1.0",
      "trace_schema": "wherecode://protocols/react_trace/v1"
    }
  },
  "agent_trace": {
    "standard": "ReAct",
    "version": "1.0",
    "loop_state": "final",
    "steps": [
      {"index": 1, "phase": "plan", "content": "analyze requirement", "status": "ok"},
      {"index": 2, "phase": "act", "content": "dispatch executor", "status": "ok"},
      {"index": 3, "phase": "observe", "content": "execution completed", "status": "ok"}
    ],
    "final_decision": "success",
    "truncated": false
  }
}
```
