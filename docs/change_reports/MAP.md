# Change Report Map (Compact)

## A) Foundation (K1-K50)

- Date range: `2026-03-01` ~ `2026-03-03`
- Main topics:
  - workflow model / scheduler / API
  - gate + rollback + policy chain
  - persistence + rehearsal + milestone entry
- Representative:
  - `2026-03-01-k1-t6-overall-flow-runnable.md`
  - `2026-03-02-k40-restore-integrity-gate.md`
  - `2026-03-03-k50-test-entry-milestone-gate.md`

## B) TST2 Automation Batch

- Date range: `2026-03-04`
- Main topics:
  - soak daemon / checkpoint / watch / autopilot
  - rehearsal latest summary
  - action-layer llm route + env loading
- Representative:
  - `2026-03-04-tst2-soak-daemonization.md`
  - `2026-03-04-tst2-autopilot-pipeline.md`
  - `2026-03-04-action-layer-mandatory-llm.md`

## C) Workflow Decompose Hardening

- Date range: `2026-03-05`
- Main topics:
  - chief decompose output coverage/mapping/task-packages
  - human confirmation + pending/preview observability
  - validation scope/task-board/release triggers
- Representative:
  - `2026-03-05-chief-decompose-coverage-hardening.md`
  - `2026-03-05-chief-decompose-human-confirm-gate.md`
  - `2026-03-05-test-strategy-tiering.md`
  - `2026-03-05-main-business-orchestrate-balanced-profile-echo.md`
  - `2026-03-05-main-business-orchestration-advance.md`
  - `2026-03-05-main-business-decompose-advance-api.md`
  - `2026-03-05-main-business-decompose-advance-loop-api.md`
  - `2026-03-05-main-business-decompose-aggregate-status.md`
  - `2026-03-05-main-business-execute-entry-auto-advance.md`
  - `2026-03-05-main-business-orchestrate-decision-report.md`
  - `2026-03-05-main-business-orchestrate-entrypoint.md`
  - `2026-03-05-main-business-orchestrate-recovery-hints.md`
  - `2026-03-05-main-business-orchestrate-recovery-scoring.md`
  - `2026-03-05-main-business-orchestrate-strategy-mode.md`
  - `2026-03-05-main-business-orchestrate-summary-upgrade.md`
  - `2026-03-05-main-business-orchestrate-telemetry-snapshot.md`
  - `2026-03-05-main-business-orchestrate-telemetry-latest-api.md`
  - `2026-03-05-main-business-decompose-preview-api.md`
  - `2026-03-05-main-business-decompose-preview-cache.md`
  - `2026-03-05-main-business-decompose-preview-gate.md`
  - `2026-03-05-main-business-decompose-preview-status-no-gate.md`

## D) Boundary and Cleanup

- Date range: `2026-03-05`
- Main topics:
  - subproject boundary reset
  - historical doc cleanup and terminology normalization
- Representative:
  - `2026-03-05-subproject-boundary-cleanup.md`
  - `2026-03-05-history-doc-boundary-cleanup.md`

## E) Main Business Recovery Loop

- Date range: `2026-03-06`
- Main topics:
  - execute decision recovery action directly from orchestrate
  - connect recommendation output with runnable recovery API
- Representative:
  - `2026-03-06-main-business-orchestrate-recovery-execute-api.md`

## F) Main Business Planning Reset

- Date range: `2026-03-06`
- Main topics:
  - milestone timeline reset with date expectations
  - sync plan / release map / task board to same execution track
- Representative:
  - `2026-03-06-main-business-milestone-plan-reset.md`

## G) README Bilingual Alignment

- Date range: `2026-03-06`
- Main topics:
  - sync EN/ZH roadmap and sprint sections
  - keep bilingual README structure aligned
- Representative:
  - `2026-03-06-readme-bilingual-sync.md`

## H) README Mirror Heading Order

- Date range: `2026-03-06`
- Main topics:
  - enforce one-to-one section order between EN/ZH README
  - normalize bilingual heading labels for fast cross-language scan
- Representative:
  - `2026-03-06-readme-bilingual-mirror-order.md`

## I) Release Map Bilingual Mirror

- Date range: `2026-03-06`
- Main topics:
  - mirror EN/ZH heading style in release map
  - keep milestone timeline/gates stable while improving bilingual readability
- Representative:
  - `2026-03-06-release-map-bilingual-mirror.md`

## J) Task Board Bilingual Mirror

- Date range: `2026-03-06`
- Main topics:
  - mirror EN/ZH heading and table structure in task board
  - keep MB2 sprint and release-track status unchanged
- Representative:
  - `2026-03-06-task-board-bilingual-mirror.md`

## K) PLAN Bilingual Mirror

- Date range: `2026-03-06`
- Main topics:
  - mirror EN/ZH heading and table structure in plan
  - keep milestone timeline and task status unchanged
- Representative:
  - `2026-03-06-plan-bilingual-mirror.md`

## L) Runbook Bilingual Mirror

- Date range: `2026-03-06`
- Main topics:
  - mirror EN/ZH heading structure in runbook
  - keep operational commands unchanged
- Representative:
  - `2026-03-06-runbook-bilingual-mirror.md`

## M) Main Business Command Orchestrate Policy

- Date range: `2026-03-06`
- Main topics:
  - route prefixed command intents into orchestrate workflow flow
  - persist workflow run and orchestration result in command/task metadata
- Representative:
  - `2026-03-06-main-business-command-orchestrate-policy.md`
  - `2026-03-06-main-business-command-workflow-state-persistence.md`
  - `2026-03-06-main-business-mb2-t3-min-e2e-contracts.md`
  - `2026-03-06-main-business-mb2-t4-runbook-api-doc-sync.md`

## N) Main Business MB3 Dry-Run Seed Tooling

- Date range: `2026-03-06`
- Main topics:
  - add MB3 seed script for `project/task/command` bootstrap and command terminal polling
  - add unified `stationctl` entry for MB3 dry-run execution
  - allow blocked/non-success command output to keep evidence when `workflow_run_id` exists
  - capture one real dry-run evidence with recovery hint (`retry_with_decompose_payload`)
  - sync MB3 sprint status and operation docs in plan/release/task-board/readme
- Representative:
  - `2026-03-06-main-business-mb3-dry-run-seed-tooling.md`

## O) Main Business MB3 T4 Recovery Execute

- Date range: `2026-03-06`
- Main topics:
  - execute orchestrate recovery action from latest blocked MB3 dry-run run
  - persist MB3-T4 recovery evidence (`action_status=executed`) for follow-up unblock flow
  - sync sprint status (`MB3-T4 done`, `MB3-T5 todo`) in plan/task-board/readme
- Representative:
  - `2026-03-06-main-business-mb3-t4-recovery-execute.md`

## P) Main Business MB3 T5 Unblock Flow

- Date range: `2026-03-06`
- Main topics:
  - add synthetic decomposition fallback when chief action returns non-success
  - clear MB3 blocked path and capture full-loop evidence (`dry-run -> recover -> execute`)
  - move milestone status to `MB3 done`
- Representative:
  - `2026-03-06-main-business-mb3-t5-unblock-flow.md`

## Q) Main Business MB4 Release Gate Readiness

- Date range: `2026-03-06`
- Main topics:
  - run release baseline gate and verify green result
  - align workflow execute metrics/contract assertions with current behavior
  - move active sprint to MB4 (`MB4-T1 done`, `MB4-T2 doing`)
- Representative:
  - `2026-03-06-main-business-mb4-release-gate-readiness.md`

## R) Main Business MB4 T2/T3 Decision Package

- Date range: `2026-03-06`
- Main topics:
  - compile MB4 release-readiness evidence package from gate + runtime artifacts
  - produce MB4 go/no-go draft and move roadmap state to `MB4 done / MB5 doing`
  - sync plan/task-board/release-map/README milestone status
- Representative:
  - `2026-03-06-main-business-mb4-t2-evidence-package.md`
  - `2026-03-06-main-business-mb4-t3-go-no-go-draft.md`

## S) Main Business MB5 Launch Decision Closure

- Date range: `2026-03-06`
- Main topics:
  - consolidate MB5 acceptance package from MB3/MB4 evidence
  - pass strict milestone gate (`tst2-ready --strict`)
  - complete launch recommendation and close MB5 milestone
- Representative:
  - `2026-03-06-main-business-mb5-t1-acceptance-package.md`
  - `2026-03-06-main-business-mb5-t2-strict-milestone-gate.md`
  - `2026-03-06-main-business-mb5-t3-launch-recommendation.md`

## T) REL1 Signoff and GO1 Kickoff

- Date range: `2026-03-06`
- Main topics:
  - publish REL1 bilingual release notes from MB5 GO recommendation
  - package REL1 signoff artifacts with strict milestone gate proof
  - move active sprint from REL1 completion to GO1 launch prep
- Representative:
  - `2026-03-06-rel1-t1-release-notes.md`
  - `2026-03-06-rel1-t2-signoff-package.md`

## U) GO1 Rehearsal and GO2 Kickoff

- Date range: `2026-03-06`
- Main topics:
  - run GO1 launch rehearsal (`check_all release` + key route sanity)
  - execute post-launch sanity checklist with full-stack smoke evidence
  - close GO1 and move active sprint to GO2 stability observation
- Representative:
  - `2026-03-06-go1-t1-launch-rehearsal.md`
  - `2026-03-06-go1-t2-post-launch-checklist.md`

## V) GO2 Stability Observation Checkpoint 01

- Date range: `2026-03-06`
- Main topics:
  - execute GO2 checkpoint with smoke + key route sanity + strict milestone gate
  - persist checkpoint evidence logs and milestone-gate artifact
  - move GO2 progress to `T1 done`, `T2 doing`
- Representative:
  - `2026-03-06-go2-t1-stability-observation-checkpoint.md`

## W) GO2 Observation Queue and GO3 Kickoff

- Date range: `2026-03-06`
- Main topics:
  - consolidate GO2 checkpoint findings into observation queue
  - close GO2 milestone with documented follow-up priorities
  - move active sprint to GO3 target-host provider/recovery validation
- Representative:
  - `2026-03-06-go2-t2-observation-queue.md`

## X) Main Flow Full-Run Completion Assessment

- Date range: `2026-03-06`
- Main topics:
  - run one complete local main-flow replay with recover + execute evidence
  - rerun release and strict milestone gates as assessment baseline
  - output weighted completion score and remaining risk focus
- Representative:
  - `2026-03-06-main-flow-full-run-assessment.md`

## Y) GO3 Target-Host Validation Package

- Date range: `2026-03-06`
- Main topics:
  - run provider/network readiness checks for target-host path
  - execute recovery-drill profile and classify failure taxonomy
  - produce validation package and move sprint to GO4 remediation
- Representative:
  - `2026-03-06-go3-t1-provider-readiness-validation.md`
  - `2026-03-06-go3-t2-recovery-taxonomy-package.md`

## Z) GO4 Provider Remediation Checkpoint

- Date range: `2026-03-06`
- Main topics:
  - add reusable provider probe script with redacted output
  - identify provider auth root cause (`invalid_api_key` from codex auth path)
  - produce GO4 remediation checklist and keep GO4-T1 in progress
- Representative:
  - `2026-03-06-go4-t1-provider-remediation-checkpoint.md`

## AA) GO4 Runtime + Recovery Closure

- Date range: `2026-03-06`
- Main topics:
  - align action-layer runtime with local codex config (`wire_api` + `User-Agent` + retry)
  - harden provider probe and recovery drill for real LLM multi-round flow
  - close GO4 gate with provider execute + recovery drill pass evidence
- Representative:
  - `2026-03-06-go4-t2-provider-runtime-recovery-closure.md`
