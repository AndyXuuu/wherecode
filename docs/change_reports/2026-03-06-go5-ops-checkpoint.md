# DOC-2026-03-06-GO5-OPS-CHECKPOINT

## Scope

- Add GO5 continuous ops checkpoint script with quick/full profiles.
- Integrate GO5 checkpoint into unified check entry (`check_all`, `stationctl`).
- Sync milestone/docs status to GO5 completed.

## Changed Files

- `PLAN.md`
- `README.md`
- `README.zh-CN.md`
- `docs/release_map.md`
- `docs/v3_task_board.md`
- `scripts/check_all.sh`
- `scripts/stationctl.sh`
- `scripts/README.md`
- `scripts/go5_ops_checkpoint.sh`

## Validation

- `bash -n scripts/go5_ops_checkpoint.sh scripts/check_all.sh scripts/stationctl.sh`
- `bash scripts/check_all.sh ops`
- `bash scripts/stationctl.sh check ops`
