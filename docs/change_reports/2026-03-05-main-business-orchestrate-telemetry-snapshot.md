# DOC-2026-03-05-MAIN-BUSINESS-ORCHESTRATE-TELEMETRY-SNAPSHOT

## Scope

- Add `telemetry_snapshot` to orchestrate response.
- Expose orchestration runtime, action count, workitem/unfinished deltas, and next-action transition.
- Include execute outcome summary (`run_status`, `failed_count`, `remaining_pending_count`) in snapshot.

## Changed Files

- `PLAN.md`
- `control_center/main.py`
- `control_center/models/api.py`
- `control_center/models/__init__.py`
- `control_center/README.md`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `control_center/.venv/bin/python -m py_compile control_center/main.py control_center/models/api.py control_center/models/__init__.py`
