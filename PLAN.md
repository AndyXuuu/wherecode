# WhereCode PLAN V3

Updated: 2026-03-13

## Workflow DNA

1. Update plan first.
2. Implement changes.
3. Run checks.
4. Update docs.

## Ownership

- AI executes end-to-end delivery.
- User provides goals/suggestions only.

## Milestones (Current)

| ID | Target | Scope | Exit Gate | Status |
| --- | --- | --- | --- | --- |
| V3-M1 | Week 1 | overlap de-dup baseline | overlap audit published; duplicated execution scope marked delegated | done |
| V3-M2 | Week 2 | adapter-first integration | OpenCode/OhMy adapters callable from control-plane with unified result schema | done |
| V3-M3 | Week 3 | clarification-first + no-guess | ambiguous requirements enter `clarifying`; unresolved blocks implement | done |
| V3-M4 | Week 4 | SDD runtime loop | `intent -> spec -> design -> tasks -> implement -> verify -> accept` runnable with artifact gates | done |
| V3-M5 | Week 5 | acceptance gate hardening | done requires evidence completeness and required checks | done |
| V3-M6 | Week 6 | remote visibility API | mobile/API can query timeline, artifacts, and final report | done |

## Current Sprint (Ordered)

| ID | Task | Owner | Depends | Status |
| --- | --- | --- | --- | --- |
| V3-T22 | split remaining workspace changes into module-based commits (`control/executor`, `scripts/tests`, `docs/layout`) | chief-architect | V3-T21 | doing |
| V3-T17 | milestone closeout M2 adapter-first integration gate (single adapter dual strategy + routing contract) | chief-architect | V3-T16 | done |
| V3-T18 | milestone closeout M3 clarification-first gate (ambiguous input -> clarifying, unresolved blocks implement) | chief-architect | V3-T17 | done |
| V3-T19 | milestone closeout M4 SDD stage chain gate (ordered stage transitions + artifact block) | chief-architect | V3-T18 | done |
| V3-T20 | milestone closeout M5 acceptance evidence gate (`accepted` only with complete evidence) | chief-architect | V3-T19 | done |
| V3-T21 | milestone closeout M6 visibility API gate + end-to-end (`main-orchestrate`, `check_all main`) | chief-architect | V3-T20 | done |
| V3-T16 | remove unused imports/method-local vars across `control_center`, `scripts`, `tests` and keep lint clean baseline (`F401/F841`) | chief-architect | V3-T15 | done |
| V3-T09 | audit feature overlap with OpenCode/OhMyOpenCode and classify keep/remove/delegate boundaries | chief-architect | V3-T08 | done |
| V3-T10 | replan V3 milestones based on overlap audit (integration-first roadmap) | chief-architect | V3-T09 | done |
| V3-T11 | hard cut V3 main path: remove V2 execution entries (`v2-*`, `subproject-*`) and keep control-plane only flow | chief-architect | V3-T10 | done |
| V3-T12 | implement single `opencode` adapter with `strategy=native|ohmy` and role routing policy as single source of truth | chief-architect | V3-T11 | done |
| V3-T13 | implement requirement clarification gate + SDD stage artifact gate (`intent->spec->design->tasks->implement->verify->accept`) | chief-architect | V3-T12 | done |
| V3-T14 | expose `/v3/runs/{id}/timeline|artifacts|report` and enforce acceptance evidence gate (`accepted` only when complete) | chief-architect | V3-T13 | done |
| V3-T15 | cleanup legacy scripts and residual V2 artifacts across repository folders | chief-architect | V3-T14 | done |
| V3-T03 | remove V3-unrelated legacy files (V2 docs/reports/derived subprojects) and keep V3-only baseline | chief-architect | V3-T02 | done |
| V3-T07 | standardize role profile directories (`.agents/roles`) and keep backward-compatible loading from `action_layer/agents` | chief-architect | V3-T03 | done |
| V3-T08 | add custom extension structure (`.agents/skills/.agents/policies/.agents/mcp`) and publish routing/context isolation policy | chief-architect | V3-T07 | done |

## Run Commands

- `bash scripts/stationctl.sh main-orchestrate`
- `bash scripts/stationctl.sh plan-autopilot`
- `bash scripts/check_all.sh main`

## V3 References

- `docs/V3_PROJECT_PLAN.md`
- `docs/V3_ENGINEERING_LAYOUT.md`
- `docs/V3_OVERLAP_AUDIT.md`

## Task Log (Recent)

- 2026-03-13 `DOC-2026-03-13-V3-T22-COMMIT-SPLIT` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T21-M6-E2E-CLOSEOUT` completed (`done`) (evidence: `main-orchestrate` success, `check_all main` success, run=`chk_1d6fbdb972dc`)
- 2026-03-13 `DOC-2026-03-13-V3-T21-M6-E2E-CLOSEOUT` resumed (`doing`) (unblock retry started)
- 2026-03-13 `DOC-2026-03-13-V3-T21-M6-E2E-CLOSEOUT` blocked (`blocked`) (attempt=2, reason=control center not reachable at `127.0.0.1:8000` for `main-orchestrate` and remote `check_all main`; local fallback `check_all main --local` passed)
- 2026-03-13 `DOC-2026-03-13-V3-T21-M6-E2E-CLOSEOUT` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T21-M6-E2E-CLOSEOUT` blocked (`doing`) (attempt=1, reason=`main_orchestrate.sh` empty array expansion with `set -u` -> `normalized_args[@]: unbound variable`)
- 2026-03-13 `DOC-2026-03-13-V3-T20-M5-CLOSEOUT` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T19-M4-CLOSEOUT` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T18-M3-CLOSEOUT` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T17-M2-CLOSEOUT` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T17-M2-CLOSEOUT` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T16-UNUSED-CLEANUP` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T16-UNUSED-CLEANUP` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T15-REPO-CLEANUP` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T15-REPO-CLEANUP` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T14-VISIBILITY-API` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T13-GATE-CHAIN` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T12-SINGLE-ADAPTER` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T11-HARDCUT` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T11-HARDCUT-START` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T10-REPLAN` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T10-REPLAN` started (`doing`)
- 2026-03-13 `DOC-2026-03-13-V3-T09-OVERLAP-AUDIT` completed (`done`)
- 2026-03-13 `DOC-2026-03-13-V3-T09-OVERLAP-AUDIT` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V3-T08-EXTENSION-STRUCTURE` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V3-T08-EXTENSION-STRUCTURE` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V3-T07-ROLE-DIR-STANDARD` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V3-T03-CLEANUP` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V3-T03-CLEANUP` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V3-T07-ROLE-DIR-STANDARD` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V3-T02-EXECUTOR-SCAFFOLD` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V3-T01-DIRECTORY-PLANNING` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V3-PLANNING` completed (`done`)
