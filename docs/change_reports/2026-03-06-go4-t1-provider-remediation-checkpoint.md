# DOC-2026-03-06-GO4-T1-PROVIDER-REMEDIATION-CHECKPOINT

## Scope

- Execute GO4-T1 provider remediation checkpoint with root-cause probes.
- Add reusable provider probe script and produce redacted remediation evidence.

## Changed Files

- `PLAN.md`
- `docs/release_map.md`
- `docs/v3_task_board.md`
- `scripts/go4_provider_probe.sh`
- `docs/ops_reports/20260306T144823Z-go4-provider-probe.json`
- `docs/ops_reports/20260306T144823Z-go4-start-all.log`
- `docs/ops_reports/20260306T144823Z-go4-provider-remediation-report.md`
- `docs/change_reports/README.md`
- `docs/change_reports/MAP.md`

## Validation

- `bash scripts/stationctl.sh start all`
- `bash scripts/go4_provider_probe.sh`
