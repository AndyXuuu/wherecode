# DOC-2026-03-06-SECRET-LEAK-GATE

## Scope

- Add lightweight secret leak gate for local git hooks and CI.
- Block commit/push when staged content or push range matches high-risk secret patterns.
- Keep false positives lower with explicit placeholder allowlist.

## Changed Files

- `PLAN.md`
- `scripts/README.md`
- `scripts/check_secrets.sh`
- `scripts/install_githooks.sh`
- `.githooks/pre-commit`
- `.githooks/pre-push`
- `.github/workflows/secret-scan.yml`

## Validation

- `bash scripts/check_secrets.sh --working-tree`
- `bash scripts/check_secrets.sh --staged`
- `bash scripts/check_secrets.sh --range HEAD~1..HEAD`
- `bash scripts/check_secrets.sh --all-history`
- `bash scripts/install_githooks.sh`
