# WhereCode PLAN V2

Updated: 2026-03-12

## Workflow DNA

1. Update plan first.
2. Implement changes.
3. Run checks.
4. Update docs.

## Ownership

- AI executes end-to-end delivery.
- User provides goals/suggestions only.

## Milestones (Current)

| ID | Target Date | Scope | Exit Gate | Status |
| --- | --- | --- | --- | --- |
| V2-M9 | 2026-03-11 | role/context/memory foundation | role rules + context isolation + memory namespace design published and runnable baseline | done |
| V2-M11 | 2026-03-12 | capability runtime baseline (Agent/MCP) | capability lifecycle minimal APIs + one real MCP capability invoke passed | planned |
| V2-M12 | 2026-03-13 | orchestration resilience | interrupt/restart/resume/failure taxonomy loop verified with persisted state | planned |
| V2-M13 | 2026-03-14 | remote visibility API | mobile-friendly run status/artifacts/report query APIs validated | planned |
| V2-M14 | 2026-03-15 | real business autopilot acceptance | stock-sentiment requirement -> generate -> execute -> acceptance -> report full loop passed | planned |
| V2-M15 | 2026-03-16 | SDD requirement loop baseline | main-brain `sdd` mode runs `intent -> spec -> design -> tasks -> implement -> verify -> accept`; SDD agent outputs structured spec; clarification-first no-guess gate active | planned |

Completed milestones are archived in:
- `docs/PLAN_V2_COMPLETED_MILESTONES.md`

## Current Sprint (Ordered)

| ID | Task | Owner | Depends | Status |
| --- | --- | --- | --- | --- |
| V2-T82 | implement dual SDD runtime (main-brain `sdd` mode + SDD agent) with stage gates and required artifacts per stage | chief-architect | V2-T81 | doing |
| V2-T83 | implement proactive clarification no-guess flow (ambiguity detection + ask-first gate + blocked policy when unresolved) | chief-architect | V2-T82 | planned |

Completed task groups are archived in:
- `docs/PLAN_V2_COMPLETED_TASKS.md`

## Run Commands

- `bash scripts/stationctl.sh v2-run stock-sentiment`
- `bash scripts/stationctl.sh plan-autopilot`
- `bash scripts/check_all.sh v2`
- `bash scripts/check_all.sh main`

## Task Log (Recent)

- 2026-03-12 `DOC-2026-03-12-V2-T82` blocked (`doing`) (blocked: attempt=1, reason=next_action_pending:review_results, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t82/latest.json)
- 2026-03-12 `DOC-2026-03-12-V2-T84` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T84` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T83` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T83` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T82` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T82` blocked (`doing`) (blocked: attempt=1, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t82/latest.json)
- 2026-03-12 `DOC-2026-03-12-V2-T82` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-PLAN-SDD-CLEANUP-AND-ADD` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-PLAN-SDD-CLEANUP-AND-ADD` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-STANDARD-AGENTS-FILE` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-STANDARD-AGENTS-FILE` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T78` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T78` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T77` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T77` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T76` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T76` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T75` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T75` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T74` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T74` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T73` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T73` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T72` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T72` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T71` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T71` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T70` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T70` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T69` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T69` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T68` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T68` blocked (`doing`) (blocked: attempt=2, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t68/latest.json)
- 2026-03-12 `DOC-2026-03-12-V2-T68` blocked (`doing`) (blocked: attempt=1, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t68/latest.json)
- 2026-03-12 `DOC-2026-03-12-V2-T68` started (`doing`)
- 2026-03-12 `DOC-2026-03-12-V2-T67` completed (`done`)
- 2026-03-12 `DOC-2026-03-12-V2-T67` doing (fix: `orchestrate request failed: action layer unavailable: ReadTimeout`; increase timeout + client strategy)
- 2026-03-12 `DOC-2026-03-12-V2-T67` blocked (`doing`) (blocked: attempt=1, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t67/latest.json)
- 2026-03-11 `DOC-2026-03-11-V2-T67` blocked (`doing`) (blocked: attempt=2, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t67/latest.json)
- 2026-03-11 `DOC-2026-03-11-V2-T67` blocked (`doing`) (blocked: attempt=1, check /Users/andyxu/Documents/project/wherecode/docs/ops_reports/plan_autopilot/v2-t67/latest.json)
- 2026-03-11 `DOC-2026-03-11-V2-T67` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T81-STRICT-SKILL` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T81-STRICT-SKILL` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-T80-SLASH-SKILL-ENTRY` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T80-SLASH-SKILL-ENTRY` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-REACT-STANDARD-DEFINITION` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-REACT-STANDARD-DEFINITION` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-STANDARD-AGENT-REACT-ALIGNMENT` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-STANDARD-AGENT-REACT-ALIGNMENT` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-PLAN-ARCHIVE-CURRENT-SPRINT` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-PLAN-ARCHIVE-CURRENT-SPRINT` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-T63-WORKFLOW-MODE` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T63-WORKFLOW-MODE` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-T64-WORKFLOW-NEXT-COMMAND` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T64-WORKFLOW-NEXT-COMMAND` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-T65-DELIVERY-TEST-PACKAGE` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T65-DELIVERY-TEST-PACKAGE` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-T66-BENCHMARK-FUNCTION-GAP` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T66-BENCHMARK-FUNCTION-GAP` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-MILESTONE-PLAN` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-MILESTONE-PLAN` completed (`done`)
- 2026-03-11 `DOC-2026-03-11-V2-T79-PLAN-AUTOPILOT` started (`doing`)
- 2026-03-11 `DOC-2026-03-11-V2-T79-PLAN-AUTOPILOT` completed (`done`)
