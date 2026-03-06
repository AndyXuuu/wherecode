# 2026-03-04 tst2 soak detach hardening

## Scope

- Harden `tst2` soak daemon process detaching in environments without `setsid`.

## Plan update

- `DOC-2026-03-04-TST2-SOAK-DETACH-HARDENING` started (`doing`).
- `DOC-2026-03-04-TST2-SOAK-DETACH-HARDENING` completed (`done`).

## Changes

- Updated soak daemon launch strategy:
  - `/Users/andyxu/Documents/project/wherecode/scripts/tst2_soak_daemon.sh`
  - launch fallback order:
    1. `setsid` + `nohup`
    2. `python3` `subprocess.Popen(start_new_session=True)`
    3. plain `nohup`
  - start metadata now records `launch=<mode>`
  - start output now prints `launch=<mode>`
- Kept stationctl unified entry:
  - `/Users/andyxu/Documents/project/wherecode/scripts/stationctl.sh`
  - `bash scripts/stationctl.sh soak <start|status|stop|restart>`
- Updated plan:
  - `/Users/andyxu/Documents/project/wherecode/PLAN.md`

## Checks

- `bash -n scripts/tst2_soak_daemon.sh scripts/stationctl.sh`
- `bash scripts/stationctl.sh soak start`
  - sample output: `launch=python3-start_new_session`
- `bash scripts/stationctl.sh soak status --strict`
  - guard status: passed (`guard_passed=true`)
- `bash scripts/check_all.sh all`
  - backend tests: `216 passed`
  - command_center build: passed
  - project backend tests: `1 passed`
