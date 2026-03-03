# TST2-T1 soak rehearsal (2026-03-03)

## Command

```bash
SOAK_DURATION_SECONDS=60 \
SOAK_INTERVAL_SECONDS=20 \
SOAK_PROBE_RUN_COUNT=2 \
SOAK_PROBE_WORKERS=1 \
SOAK_RUN_PROBE_EACH_ROUND=true \
bash scripts/tst2_soak.sh
```

## Artifacts

- summary: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T134206Z-tst2-soak-summary.md`
- samples: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T134206Z-tst2-soak-samples.jsonl`
- probe log: `/Users/andyxu/Documents/project/wherecode/docs/ops_reports/20260303T134206Z-tst2-soak-probe.log`

## Result

- rounds: `3`
- failed run delta: `0`
- blocked run peak: `0`
- probe pass rounds: `3`
- probe fail rounds: `0`
- guard passed: `true`

## Next

- run full 24h window:
  - `SOAK_DURATION_SECONDS=86400`
  - `SOAK_INTERVAL_SECONDS=300`
- run in a persistent shell/session (not transient tool command) to avoid background process exit.
