# GO4 Provider Remediation Report (Checkpoint 01)

Generated: 2026-03-06T14:48:23Z
Scope: provider access remediation diagnosis and actionable checklist

## Evidence

- Provider probe (redacted): `docs/ops_reports/20260306T144823Z-go4-provider-probe.json`
- GO3 validation package: `docs/ops_reports/20260306T143648Z-go3-target-host-validation-package.md`
- Recovery drill taxonomy: `docs/ops_reports/20260306T143648Z-go3-recovery-drill-classification.json`

## Diagnosis

- Local control/action/proxy health: PASS (`200`).
- Provider endpoint connectivity: reachable (`/v1/models` responds).
- Provider auth state: FAIL (`401`, `invalid_api_key`).

## Root Cause

- Current key source is `codex_auth`.
- The key resolved from Codex auth is invalid for provider request path.

## Remediation Checklist

1. Rotate or replace `OPENAI_API_KEY` in `${CODEX_HOME:-$HOME/.codex}/auth.json`.
2. If target host uses `.env`, set valid `ACTION_LAYER_LLM_API_KEY` there.
3. Restart services: `bash scripts/stationctl.sh restart all`.
4. Re-run probe: `bash scripts/go4_provider_probe.sh`.
5. Gate for remediation pass:
   - `provider_models.http_code` must be `200`.
   - `bash scripts/action_layer_llm_check.sh` must exit `0`.
   - `bash scripts/v3_recovery_drill.sh` must exit `0`.

## Decision

- GO4-T1 status: in progress (root cause confirmed, key replacement pending).
