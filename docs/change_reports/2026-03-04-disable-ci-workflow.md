# 2026-03-04 disable CI workflow

## Scope

- Remove GitHub CI workflow that keeps failing.

## Plan update

- `DOC-2026-03-04-DISABLE-CI-WORKFLOW` started (`doing`).
- `DOC-2026-03-04-DISABLE-CI-WORKFLOW` completed (`done`).

## Changes

- Removed workflow file:
  - `/Users/andyxu/Documents/project/wherecode/.github/workflows/ci.yml`
- Kept scheduled metrics workflow:
  - `/Users/andyxu/Documents/project/wherecode/.github/workflows/nightly-metrics.yml`

## Checks

- `bash scripts/check_all.sh`
  - backend tests: `205 passed`
  - command_center build: passed
