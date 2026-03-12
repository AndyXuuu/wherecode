# Delivery Test Package (V2)

Updated: 2026-03-11

## Scope

This package validates whether main flow + V2 flow are ready for handoff to formal testing.

## Gate Checklist

1. Script syntax gate
- `bash -n scripts/go8_subproject_full_cycle.sh scripts/v2_run.sh scripts/v2_replay.sh scripts/v2_gate.sh`
- Status: pass

2. Main scope gate
- `bash scripts/check_all.sh main --local`
- Status: pass

3. V2 scope gate
- `bash scripts/check_all.sh v2 --local`
- Status: pass

4. Release baseline gate
- `bash scripts/check_all.sh release --local`
- Status: pass

## Flow Acceptance Evidence

### A) One-shot build (`workflow-mode=test`)

- Command:
  - `bash scripts/v2_run.sh stock-sentiment-deliverycheck --mode build --workflow-mode test --requirement-file project/requirements/stock-sentiment.md --execute false --force-clean true --stamp 20260311T134500Z`
- V2 report:
  - `docs/v2_reports/20260311T134500Z-stock-sentiment-deliverycheck-v2-run.json`
- Latest pointer:
  - `docs/v2_reports/latest_stock-sentiment-deliverycheck_v2_run.json`
- Expected state:
  - `outputs.workflow_stage_executed = acceptance`
  - `outputs.workflow_next_stage = done`
  - `outputs.workflow_complete = true`
- Gate:
  - `bash scripts/v2_gate.sh --subproject stock-sentiment-deliverycheck --latest docs/v2_reports/latest_stock-sentiment-deliverycheck_v2_run.json`
  - Status: pass

### B) Stepwise build (`workflow-mode=dev`)

- Commands:
  - `bash scripts/v2_run.sh stock-sentiment-deliverydev --mode build --workflow-mode dev --reset-dev-state true --requirement-file project/requirements/stock-sentiment.md --execute false --force-clean true --stamp 20260311T134600Z`
  - `bash scripts/v2_run.sh stock-sentiment-deliverydev --mode build --workflow-mode dev --requirement-file project/requirements/stock-sentiment.md --execute false --force-clean false --stamp 20260311T134600Z`
  - `bash scripts/v2_run.sh stock-sentiment-deliverydev --mode build --workflow-mode dev --requirement-file project/requirements/stock-sentiment.md --execute false --force-clean false --stamp 20260311T134600Z`
- V2 report:
  - `docs/v2_reports/20260311T134600Z-stock-sentiment-deliverydev-v2-run.json`
- Latest pointer:
  - `docs/v2_reports/latest_stock-sentiment-deliverydev_v2_run.json`
- Expected state:
  - `outputs.workflow_stage_executed = acceptance`
  - `outputs.workflow_next_stage = done`
  - `outputs.workflow_complete = true`
  - `outputs.workflow_next_command` is not empty
  - `outputs.workflow_ops_log_path` exists
  - `outputs.workflow_state_path` exists
- Gate:
  - `bash scripts/v2_gate.sh --subproject stock-sentiment-deliverydev --latest docs/v2_reports/latest_stock-sentiment-deliverydev_v2_run.json`
  - Status: pass

## Blocking Issue Fixed In This Cycle

- Issue:
  - `check_all release --local` failed because backend full pytest collected generated subproject tests under `project/*`.
- Root cause:
  - `scripts/check_backend.sh full` executed `pytest -q` from repo root (over-broad discovery).
- Fix:
  - changed to `pytest -q tests` in `scripts/check_backend.sh`.
- Validation:
  - rerun `bash scripts/check_all.sh release --local` -> pass.

## Delivery Decision

- Status: ready for formal testing handoff.
- Remaining operational caution:
  - For `workflow-mode=dev`, execute commands serially for the same `stamp` to avoid duplicate same-stage runs.
