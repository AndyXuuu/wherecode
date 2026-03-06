# REL1 Release Notes (Main Business)

Date: 2026-03-06
Scope: single-host local deployment

## Summary

- Release stage advanced to `REL1` after MB5 closure.
- Main workflow path is closed and evidenced: `command -> orchestrate -> recover -> execute`.
- Strict milestone gate passed: `tst2-ready --strict`.

## Included in REL1

- MB3 dry-run + recover + execute full-loop evidence.
- MB4 readiness package and go/no-go draft.
- MB5 acceptance package and launch recommendation (`GO`).
- Synthetic decomposition fallback for chief non-success responses (default enabled).

## Operational Conditions

- Keep `WHERECODE_DECOMPOSE_ALLOW_SYNTHETIC_FALLBACK=true`.
- Run `bash scripts/check_all.sh release` before each release cut.
- Keep operator confirmation when decomposition confirmation is required.

## Validation Snapshot

- `bash scripts/v3_milestone_gate.sh --milestone tst2-ready --strict`: passed.
- Last recommendation: promote to `REL1` release signoff.

## Known Limits

- External provider instability can affect decomposition/output quality.
- This signoff is for single-host local scope, not multi-host HA.

## References

- `docs/ops_reports/20260306T135435Z-mb5-acceptance-package.md`
- `docs/ops_reports/20260306T135435Z-mb5-launch-recommendation.md`
- `docs/ops_reports/20260306T134912Z-mb4-readiness-package.md`
- `docs/ops_reports/20260306T134912Z-mb4-go-no-go-draft.md`
- `docs/ops_reports/20260306T134242Z-mb3-t5-full-loop.json`
