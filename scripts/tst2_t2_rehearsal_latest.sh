#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${TST2_T2_REPORT_DIR:-${ROOT_DIR}/docs/ops_reports}"
LATEST_REPORT_PATH="${TST2_T2_LATEST_REPORT_PATH:-${REPORT_DIR}/latest_tst2_t2_release_rehearsal.md}"
LATEST_SUMMARY_PATH="${TST2_T2_LATEST_SUMMARY_PATH:-${REPORT_DIR}/latest_tst2_t2_release_rehearsal.json}"
PATH_ONLY=false
STRICT_MODE=false

usage() {
  cat <<'EOF'
Usage:
  bash scripts/tst2_t2_rehearsal_latest.sh [--path-only] [--strict]

Options:
  --path-only   only print latest report path
  --strict      exit non-zero when latest report not found
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path-only)
      PATH_ONLY=true
      ;;
    --strict)
      STRICT_MODE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

if [[ ! -f "${LATEST_REPORT_PATH}" ]]; then
  fallback="$(ls -1t "${REPORT_DIR}"/*-tst2-t2-release-rehearsal.md 2>/dev/null | head -n 1 || true)"
  if [[ -n "${fallback}" ]]; then
    cp "${fallback}" "${LATEST_REPORT_PATH}"
  fi
fi

if [[ ! -f "${LATEST_REPORT_PATH}" ]]; then
  echo "latest_tst2_t2_report_missing=true"
  if [[ "${STRICT_MODE}" == "true" ]]; then
    exit 1
  fi
  exit 0
fi

echo "latest_report=${LATEST_REPORT_PATH}"
if [[ -f "${LATEST_SUMMARY_PATH}" ]]; then
  echo "latest_summary=${LATEST_SUMMARY_PATH}"
fi

if [[ "${PATH_ONLY}" == "true" ]]; then
  echo "${LATEST_REPORT_PATH}"
  exit 0
fi

echo "--- latest report tail ---"
tail -n 20 "${LATEST_REPORT_PATH}" || true
