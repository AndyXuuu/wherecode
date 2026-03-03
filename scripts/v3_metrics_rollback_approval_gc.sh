#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/control_center/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
DRY_RUN=false
REMOVE_USED=true
REMOVE_EXPIRED=true
OLDER_THAN_SECONDS=""
KEEP_LATEST=0
PURGE_AUDITS=false
EXPORT_PURGE_AUDITS=false
EXPORT_FROM_ISO=""
EXPORT_TO_ISO=""
EXPORT_EVENT_TYPE=""
EXPORT_LIMIT=200
EXPORT_OUTPUT_PATH=""
ROTATE_EXPORTS=false
ROTATE_EXPORT_DIR=""
ROTATE_OLDER_THAN_SECONDS=""
ROTATE_KEEP_LATEST_FILES=0
MANIFEST_PATH=""
VERIFY_MANIFEST=false
VERIFY_MANIFEST_ID=""
VERIFY_EXPORT_FILE=""
MANIFEST_KEY_ID=""
MANIFEST_SIGNATURE=""
VERIFY_REPORT_OUTPUT=""
VERIFY_REPORT_FORMAT="txt"
MANIFEST_SIGNER_CMD=""
MANIFEST_SIGNER_TIMEOUT=10
SIGNER_PREFLIGHT=false
PREFLIGHT_HISTORY_PATH=""
PREFLIGHT_HISTORY_WINDOW=10
PREFLIGHT_HISTORY_WINDOW_SET=false
VERIFY_TREND_WINDOW=10
VERIFY_TREND_WINDOW_SET=false
VERIFY_ARCHIVE_DIR=""
VERIFY_FETCH_CMD=""
VERIFY_FETCH_TIMEOUT=15
VERIFY_ALLOWED_RESOLVERS=""
POLICY_PROFILE=""
POLICY_FILE_PATH=""
POLICY_SOURCE_URL=""
POLICY_SOURCE_TIMEOUT=10
POLICY_SOURCE_TOKEN="${WHERECODE_TOKEN:-}"
EXPORT_EFFECTIVE_POLICY_PATH=""
DISTRIBUTE_EFFECTIVE_POLICY_DIR=""
DISTRIBUTE_EFFECTIVE_POLICY_RETAIN_SECONDS=""
DISTRIBUTE_EFFECTIVE_POLICY_KEEP_LATEST=""
LIST_EFFECTIVE_POLICY_DISTRIBUTIONS=false
LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT=20
LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_MODE=""
LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO=""
LIST_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR=false
LIST_EFFECTIVE_POLICY_FAIL_ON_EMPTY=false
LIST_EFFECTIVE_POLICY_MIN_SELECTED=""
LIST_EFFECTIVE_POLICY_STATE_FILE=""
RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS=false
RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT=20
RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO=""
RESTORE_EFFECTIVE_POLICY_VERIFY_INTEGRITY=false
RESTORE_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR=false
RESTORE_EFFECTIVE_POLICY_REMAP_FROM=""
RESTORE_EFFECTIVE_POLICY_REMAP_TO=""
RESTORE_EFFECTIVE_POLICY_STATE_FILE=""
RESTORE_EFFECTIVE_POLICY_MIN_RESTORED=""
PREFLIGHT_SLO_MIN_PASS_RATE=""
PREFLIGHT_SLO_MAX_CONSECUTIVE_FAILURES=""
VERIFY_SLO_MIN_PASS_RATE=""
VERIFY_SLO_MAX_FETCH_FAILURES=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    --keep-used)
      REMOVE_USED=false
      ;;
    --keep-expired)
      REMOVE_EXPIRED=false
      ;;
    --older-than-seconds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --older-than-seconds"
        exit 1
      fi
      OLDER_THAN_SECONDS="$1"
      ;;
    --keep-latest)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --keep-latest"
        exit 1
      fi
      KEEP_LATEST="$1"
      ;;
    --purge-audits)
      PURGE_AUDITS=true
      ;;
    --export-purge-audits)
      EXPORT_PURGE_AUDITS=true
      ;;
    --from-iso)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --from-iso"
        exit 1
      fi
      EXPORT_FROM_ISO="$1"
      ;;
    --to-iso)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --to-iso"
        exit 1
      fi
      EXPORT_TO_ISO="$1"
      ;;
    --event-type)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --event-type"
        exit 1
      fi
      EXPORT_EVENT_TYPE="$1"
      ;;
    --limit)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --limit"
        exit 1
      fi
      EXPORT_LIMIT="$1"
      ;;
    --output)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --output"
        exit 1
      fi
      EXPORT_OUTPUT_PATH="$1"
      ;;
    --rotate-exports)
      ROTATE_EXPORTS=true
      ;;
    --export-dir)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --export-dir"
        exit 1
      fi
      ROTATE_EXPORT_DIR="$1"
      ;;
    --retain-seconds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --retain-seconds"
        exit 1
      fi
      ROTATE_OLDER_THAN_SECONDS="$1"
      ;;
    --keep-export-latest)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --keep-export-latest"
        exit 1
      fi
      ROTATE_KEEP_LATEST_FILES="$1"
      ;;
    --manifest)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manifest"
        exit 1
      fi
      MANIFEST_PATH="$1"
      ;;
    --verify-manifest)
      VERIFY_MANIFEST=true
      ;;
    --manifest-id)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manifest-id"
        exit 1
      fi
      VERIFY_MANIFEST_ID="$1"
      ;;
    --verify-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-file"
        exit 1
      fi
      VERIFY_EXPORT_FILE="$1"
      ;;
    --manifest-key-id)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manifest-key-id"
        exit 1
      fi
      MANIFEST_KEY_ID="$1"
      ;;
    --manifest-signature)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manifest-signature"
        exit 1
      fi
      MANIFEST_SIGNATURE="$1"
      ;;
    --verify-report)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-report"
        exit 1
      fi
      VERIFY_REPORT_OUTPUT="$1"
      ;;
    --verify-report-format)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-report-format"
        exit 1
      fi
      VERIFY_REPORT_FORMAT="$1"
      ;;
    --manifest-signer-cmd)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manifest-signer-cmd"
        exit 1
      fi
      MANIFEST_SIGNER_CMD="$1"
      ;;
    --manifest-signer-timeout)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --manifest-signer-timeout"
        exit 1
      fi
      MANIFEST_SIGNER_TIMEOUT="$1"
      ;;
    --signer-preflight)
      SIGNER_PREFLIGHT=true
      ;;
    --preflight-history)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --preflight-history"
        exit 1
      fi
      PREFLIGHT_HISTORY_PATH="$1"
      ;;
    --preflight-history-window)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --preflight-history-window"
        exit 1
      fi
      PREFLIGHT_HISTORY_WINDOW="$1"
      PREFLIGHT_HISTORY_WINDOW_SET=true
      ;;
    --verify-trend-window)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-trend-window"
        exit 1
      fi
      VERIFY_TREND_WINDOW="$1"
      VERIFY_TREND_WINDOW_SET=true
      ;;
    --verify-archive-dir)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-archive-dir"
        exit 1
      fi
      VERIFY_ARCHIVE_DIR="$1"
      ;;
    --verify-fetch-cmd)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-fetch-cmd"
        exit 1
      fi
      VERIFY_FETCH_CMD="$1"
      ;;
    --verify-fetch-timeout)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-fetch-timeout"
        exit 1
      fi
      VERIFY_FETCH_TIMEOUT="$1"
      ;;
    --verify-allowed-resolvers)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-allowed-resolvers"
        exit 1
      fi
      VERIFY_ALLOWED_RESOLVERS="$1"
      ;;
    --policy-profile)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --policy-profile"
        exit 1
      fi
      POLICY_PROFILE="$1"
      ;;
    --policy-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --policy-file"
        exit 1
      fi
      POLICY_FILE_PATH="$1"
      ;;
    --policy-source-url)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --policy-source-url"
        exit 1
      fi
      POLICY_SOURCE_URL="$1"
      ;;
    --policy-source-timeout)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --policy-source-timeout"
        exit 1
      fi
      POLICY_SOURCE_TIMEOUT="$1"
      ;;
    --policy-source-token)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --policy-source-token"
        exit 1
      fi
      POLICY_SOURCE_TOKEN="$1"
      ;;
    --export-effective-policy)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --export-effective-policy"
        exit 1
      fi
      EXPORT_EFFECTIVE_POLICY_PATH="$1"
      ;;
    --distribute-effective-policy-dir)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --distribute-effective-policy-dir"
        exit 1
      fi
      DISTRIBUTE_EFFECTIVE_POLICY_DIR="$1"
      ;;
    --distribute-effective-policy-retain-seconds)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --distribute-effective-policy-retain-seconds"
        exit 1
      fi
      DISTRIBUTE_EFFECTIVE_POLICY_RETAIN_SECONDS="$1"
      ;;
    --distribute-effective-policy-keep-latest)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --distribute-effective-policy-keep-latest"
        exit 1
      fi
      DISTRIBUTE_EFFECTIVE_POLICY_KEEP_LATEST="$1"
      ;;
    --list-effective-policy-distributions)
      LIST_EFFECTIVE_POLICY_DISTRIBUTIONS=true
      ;;
    --list-effective-policy-distributions-limit)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --list-effective-policy-distributions-limit"
        exit 1
      fi
      LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT="$1"
      ;;
    --list-effective-policy-distributions-mode)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --list-effective-policy-distributions-mode"
        exit 1
      fi
      LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_MODE="$1"
      ;;
    --list-effective-policy-distributions-since-iso)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --list-effective-policy-distributions-since-iso"
        exit 1
      fi
      LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO="$1"
      ;;
    --list-effective-policy-fail-on-integrity-error)
      LIST_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR=true
      ;;
    --list-effective-policy-fail-on-empty)
      LIST_EFFECTIVE_POLICY_FAIL_ON_EMPTY=true
      ;;
    --list-effective-policy-min-selected)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --list-effective-policy-min-selected"
        exit 1
      fi
      LIST_EFFECTIVE_POLICY_MIN_SELECTED="$1"
      ;;
    --list-effective-policy-state-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --list-effective-policy-state-file"
        exit 1
      fi
      LIST_EFFECTIVE_POLICY_STATE_FILE="$1"
      ;;
    --restore-effective-policy-distributions)
      RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS=true
      ;;
    --restore-effective-policy-distributions-limit)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --restore-effective-policy-distributions-limit"
        exit 1
      fi
      RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT="$1"
      ;;
    --restore-effective-policy-distributions-since-iso)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --restore-effective-policy-distributions-since-iso"
        exit 1
      fi
      RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO="$1"
      ;;
    --restore-effective-policy-verify-integrity)
      RESTORE_EFFECTIVE_POLICY_VERIFY_INTEGRITY=true
      ;;
    --restore-effective-policy-fail-on-integrity-error)
      RESTORE_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR=true
      ;;
    --restore-effective-policy-remap-from)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --restore-effective-policy-remap-from"
        exit 1
      fi
      RESTORE_EFFECTIVE_POLICY_REMAP_FROM="$1"
      ;;
    --restore-effective-policy-remap-to)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --restore-effective-policy-remap-to"
        exit 1
      fi
      RESTORE_EFFECTIVE_POLICY_REMAP_TO="$1"
      ;;
    --restore-effective-policy-state-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --restore-effective-policy-state-file"
        exit 1
      fi
      RESTORE_EFFECTIVE_POLICY_STATE_FILE="$1"
      ;;
    --restore-effective-policy-min-restored)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --restore-effective-policy-min-restored"
        exit 1
      fi
      RESTORE_EFFECTIVE_POLICY_MIN_RESTORED="$1"
      ;;
    --preflight-slo-min-pass-rate)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --preflight-slo-min-pass-rate"
        exit 1
      fi
      PREFLIGHT_SLO_MIN_PASS_RATE="$1"
      ;;
    --preflight-slo-max-consecutive-failures)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --preflight-slo-max-consecutive-failures"
        exit 1
      fi
      PREFLIGHT_SLO_MAX_CONSECUTIVE_FAILURES="$1"
      ;;
    --verify-slo-min-pass-rate)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-slo-min-pass-rate"
        exit 1
      fi
      VERIFY_SLO_MIN_PASS_RATE="$1"
      ;;
    --verify-slo-max-fetch-failures)
      shift
      if [[ $# -eq 0 ]]; then
        echo "missing value for --verify-slo-max-fetch-failures"
        exit 1
      fi
      VERIFY_SLO_MAX_FETCH_FAILURES="$1"
      ;;
    *)
      echo "unknown option: $1"
      echo "usage: bash scripts/v3_metrics_rollback_approval_gc.sh [--dry-run] [--keep-used] [--keep-expired] [--older-than-seconds <seconds>] [--purge-audits] [--keep-latest <count>] [--export-purge-audits] [--from-iso <iso>] [--to-iso <iso>] [--event-type <type>] [--limit <n>] [--output <file>] [--rotate-exports] [--export-dir <dir>] [--retain-seconds <seconds>] [--keep-export-latest <count>] [--manifest <file>] [--manifest-key-id <id>] [--manifest-signature <value>] [--manifest-signer-cmd <cmd>] [--manifest-signer-timeout <seconds>] [--signer-preflight] [--preflight-history <file>] [--preflight-history-window <count>] [--preflight-slo-min-pass-rate <0..1>] [--preflight-slo-max-consecutive-failures <n>] [--verify-manifest] [--manifest-id <id>] [--verify-file <file>] [--verify-report <file>] [--verify-report-format txt|json] [--verify-trend-window <count>] [--verify-archive-dir <dir>] [--verify-fetch-cmd <cmd>] [--verify-fetch-timeout <seconds>] [--verify-allowed-resolvers <csv>] [--verify-slo-min-pass-rate <0..1>] [--verify-slo-max-fetch-failures <n>] [--policy-profile strict|standard|degraded|custom] [--policy-file <file>] [--policy-source-url <url>] [--policy-source-timeout <seconds>] [--policy-source-token <token>] [--export-effective-policy <file>] [--distribute-effective-policy-dir <dir>] [--distribute-effective-policy-retain-seconds <seconds>] [--distribute-effective-policy-keep-latest <count>] [--list-effective-policy-distributions] [--list-effective-policy-distributions-limit <count>] [--list-effective-policy-distributions-mode verify_manifest|signer_preflight] [--list-effective-policy-distributions-since-iso <iso>] [--list-effective-policy-fail-on-integrity-error] [--list-effective-policy-fail-on-empty] [--list-effective-policy-min-selected <count>] [--list-effective-policy-state-file <path>] [--restore-effective-policy-distributions] [--restore-effective-policy-distributions-limit <count>] [--restore-effective-policy-distributions-since-iso <iso>] [--restore-effective-policy-verify-integrity] [--restore-effective-policy-fail-on-integrity-error] [--restore-effective-policy-remap-from <path>] [--restore-effective-policy-remap-to <path>] [--restore-effective-policy-state-file <path>] [--restore-effective-policy-min-restored <count>]"
      exit 1
      ;;
  esac
  shift
done

if [[ "${PURGE_AUDITS}" == "true" && "${EXPORT_PURGE_AUDITS}" == "true" ]]; then
  echo "invalid mode: --purge-audits and --export-purge-audits cannot be used together"
  exit 1
fi

if [[ "${VERIFY_MANIFEST}" == "true" && ("${PURGE_AUDITS}" == "true" || "${EXPORT_PURGE_AUDITS}" == "true" || "${ROTATE_EXPORTS}" == "true") ]]; then
  echo "invalid mode: --verify-manifest cannot be combined with purge/export/rotate modes"
  exit 1
fi

if [[ "${SIGNER_PREFLIGHT}" == "true" && ("${PURGE_AUDITS}" == "true" || "${EXPORT_PURGE_AUDITS}" == "true" || "${ROTATE_EXPORTS}" == "true" || "${VERIFY_MANIFEST}" == "true") ]]; then
  echo "invalid mode: --signer-preflight cannot be combined with purge/export/rotate/verify modes"
  exit 1
fi

if [[ "${ROTATE_EXPORTS}" == "true" && ("${PURGE_AUDITS}" == "true" || "${EXPORT_PURGE_AUDITS}" == "true") ]]; then
  echo "invalid mode: --rotate-exports cannot be combined with purge/export modes"
  exit 1
fi

if [[ "${PURGE_AUDITS}" == "true" && -z "${OLDER_THAN_SECONDS}" && "${KEEP_LATEST}" == "0" ]]; then
  echo "safety check failed: use --older-than-seconds or --keep-latest when --purge-audits is set"
  exit 1
fi

if [[ "${ROTATE_EXPORTS}" == "true" ]]; then
  if [[ -z "${ROTATE_EXPORT_DIR}" ]]; then
    echo "missing --export-dir for --rotate-exports mode"
    exit 1
  fi
  if [[ -z "${ROTATE_OLDER_THAN_SECONDS}" && "${ROTATE_KEEP_LATEST_FILES}" == "0" ]]; then
    echo "safety check failed: use --retain-seconds or --keep-export-latest when --rotate-exports is set"
    exit 1
  fi
fi

if [[ "${VERIFY_MANIFEST}" == "true" && -z "${MANIFEST_PATH}" ]]; then
  echo "missing --manifest for --verify-manifest mode"
  exit 1
fi

if [[ "${EXPORT_PURGE_AUDITS}" == "true" && -n "${MANIFEST_PATH}" && -z "${EXPORT_OUTPUT_PATH}" ]]; then
  echo "invalid export mode: --manifest requires --output"
  exit 1
fi

if [[ "${EXPORT_PURGE_AUDITS}" == "true" && -z "${MANIFEST_PATH}" && (-n "${MANIFEST_KEY_ID}" || -n "${MANIFEST_SIGNATURE}") ]]; then
  echo "invalid export mode: --manifest-key-id/--manifest-signature require --manifest"
  exit 1
fi

if [[ -n "${VERIFY_REPORT_OUTPUT}" && "${VERIFY_MANIFEST}" != "true" ]]; then
  echo "invalid mode: --verify-report requires --verify-manifest"
  exit 1
fi

if [[ "${VERIFY_MANIFEST}" == "true" && "${VERIFY_REPORT_FORMAT}" != "txt" && "${VERIFY_REPORT_FORMAT}" != "json" ]]; then
  echo "invalid value: --verify-report-format must be txt or json"
  exit 1
fi

if [[ "${EXPORT_PURGE_AUDITS}" == "true" && -n "${MANIFEST_SIGNER_CMD}" && -z "${MANIFEST_PATH}" ]]; then
  echo "invalid export mode: --manifest-signer-cmd requires --manifest"
  exit 1
fi

if [[ "${SIGNER_PREFLIGHT}" == "true" && -z "${MANIFEST_SIGNER_CMD}" ]]; then
  echo "invalid mode: --signer-preflight requires --manifest-signer-cmd"
  exit 1
fi

if [[ "${VERIFY_MANIFEST}" != "true" && "${VERIFY_TREND_WINDOW_SET}" == "true" ]]; then
  echo "invalid mode: --verify-trend-window requires --verify-manifest"
  exit 1
fi

if [[ "${VERIFY_MANIFEST}" != "true" && -n "${VERIFY_ARCHIVE_DIR}" ]]; then
  echo "invalid mode: --verify-archive-dir requires --verify-manifest"
  exit 1
fi

if [[ "${VERIFY_MANIFEST}" != "true" && -n "${VERIFY_FETCH_CMD}" ]]; then
  echo "invalid mode: --verify-fetch-cmd requires --verify-manifest"
  exit 1
fi

if [[ "${VERIFY_MANIFEST}" != "true" && (-n "${VERIFY_ALLOWED_RESOLVERS}" || -n "${VERIFY_SLO_MIN_PASS_RATE}" || -n "${VERIFY_SLO_MAX_FETCH_FAILURES}") ]]; then
  echo "invalid mode: verify policy options require --verify-manifest"
  exit 1
fi

if [[ "${SIGNER_PREFLIGHT}" != "true" && (-n "${PREFLIGHT_HISTORY_PATH}" || "${PREFLIGHT_HISTORY_WINDOW_SET}" == "true") ]]; then
  echo "invalid mode: --preflight-history/--preflight-history-window require --signer-preflight"
  exit 1
fi

if [[ "${SIGNER_PREFLIGHT}" != "true" && (-n "${PREFLIGHT_SLO_MIN_PASS_RATE}" || -n "${PREFLIGHT_SLO_MAX_CONSECUTIVE_FAILURES}") ]]; then
  echo "invalid mode: preflight slo options require --signer-preflight"
  exit 1
fi

if [[ "${SIGNER_PREFLIGHT}" == "true" && (-n "${PREFLIGHT_SLO_MIN_PASS_RATE}" || -n "${PREFLIGHT_SLO_MAX_CONSECUTIVE_FAILURES}") && -z "${PREFLIGHT_HISTORY_PATH}" ]]; then
  echo "invalid mode: preflight slo options require --preflight-history"
  exit 1
fi

if [[ -n "${POLICY_PROFILE}" && "${VERIFY_MANIFEST}" != "true" && "${SIGNER_PREFLIGHT}" != "true" ]]; then
  echo "invalid mode: --policy-profile requires --verify-manifest or --signer-preflight"
  exit 1
fi

if [[ -n "${POLICY_FILE_PATH}" && "${VERIFY_MANIFEST}" != "true" && "${SIGNER_PREFLIGHT}" != "true" ]]; then
  echo "invalid mode: --policy-file requires --verify-manifest or --signer-preflight"
  exit 1
fi

if [[ -n "${POLICY_SOURCE_URL}" && "${VERIFY_MANIFEST}" != "true" && "${SIGNER_PREFLIGHT}" != "true" ]]; then
  echo "invalid mode: --policy-source-url requires --verify-manifest or --signer-preflight"
  exit 1
fi

if [[ -n "${POLICY_FILE_PATH}" && -n "${POLICY_SOURCE_URL}" ]]; then
  echo "invalid mode: --policy-file and --policy-source-url cannot be used together"
  exit 1
fi

if [[ "${SIGNER_PREFLIGHT}" == "true" && -n "${POLICY_PROFILE}" && "${POLICY_PROFILE}" != "custom" && -z "${PREFLIGHT_HISTORY_PATH}" ]]; then
  echo "invalid mode: non-custom --policy-profile in preflight mode requires --preflight-history"
  exit 1
fi

if [[ -n "${EXPORT_EFFECTIVE_POLICY_PATH}" && "${VERIFY_MANIFEST}" != "true" && "${SIGNER_PREFLIGHT}" != "true" ]]; then
  echo "invalid mode: --export-effective-policy requires --verify-manifest or --signer-preflight"
  exit 1
fi

if [[ -n "${DISTRIBUTE_EFFECTIVE_POLICY_DIR}" && "${VERIFY_MANIFEST}" != "true" && "${SIGNER_PREFLIGHT}" != "true" && "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS}" != "true" && "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS}" != "true" ]]; then
  echo "invalid mode: --distribute-effective-policy-dir requires --verify-manifest or --signer-preflight"
  exit 1
fi

if [[ -n "${DISTRIBUTE_EFFECTIVE_POLICY_RETAIN_SECONDS}" && -z "${DISTRIBUTE_EFFECTIVE_POLICY_DIR}" ]]; then
  echo "invalid mode: --distribute-effective-policy-retain-seconds requires --distribute-effective-policy-dir"
  exit 1
fi

if [[ -n "${DISTRIBUTE_EFFECTIVE_POLICY_KEEP_LATEST}" && -z "${DISTRIBUTE_EFFECTIVE_POLICY_DIR}" ]]; then
  echo "invalid mode: --distribute-effective-policy-keep-latest requires --distribute-effective-policy-dir"
  exit 1
fi

if [[ "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS}" == "true" && -z "${DISTRIBUTE_EFFECTIVE_POLICY_DIR}" ]]; then
  echo "invalid mode: --list-effective-policy-distributions requires --distribute-effective-policy-dir"
  exit 1
fi

if [[ "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS}" != "true" && (-n "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_MODE}" || -n "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO}" || "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT}" != "20" || "${LIST_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR}" == "true" || "${LIST_EFFECTIVE_POLICY_FAIL_ON_EMPTY}" == "true" || -n "${LIST_EFFECTIVE_POLICY_MIN_SELECTED}" || -n "${LIST_EFFECTIVE_POLICY_STATE_FILE}") ]]; then
  echo "invalid mode: list-effective-policy-distributions filters require --list-effective-policy-distributions"
  exit 1
fi

if [[ "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS}" == "true" && ("${VERIFY_MANIFEST}" == "true" || "${SIGNER_PREFLIGHT}" == "true" || "${PURGE_AUDITS}" == "true" || "${EXPORT_PURGE_AUDITS}" == "true" || "${ROTATE_EXPORTS}" == "true") ]]; then
  echo "invalid mode: --list-effective-policy-distributions cannot be combined with verify/preflight/purge/export/rotate modes"
  exit 1
fi

if [[ "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS}" == "true" && -z "${DISTRIBUTE_EFFECTIVE_POLICY_DIR}" ]]; then
  echo "invalid mode: --restore-effective-policy-distributions requires --distribute-effective-policy-dir"
  exit 1
fi

if [[ "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS}" != "true" && (-n "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO}" || "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT}" != "20" || "${RESTORE_EFFECTIVE_POLICY_VERIFY_INTEGRITY}" == "true" || "${RESTORE_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR}" == "true" || -n "${RESTORE_EFFECTIVE_POLICY_REMAP_FROM}" || -n "${RESTORE_EFFECTIVE_POLICY_REMAP_TO}" || -n "${RESTORE_EFFECTIVE_POLICY_STATE_FILE}" || -n "${RESTORE_EFFECTIVE_POLICY_MIN_RESTORED}") ]]; then
  echo "invalid mode: restore-effective-policy-distributions filters require --restore-effective-policy-distributions"
  exit 1
fi

if [[ "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS}" == "true" && ("${VERIFY_MANIFEST}" == "true" || "${SIGNER_PREFLIGHT}" == "true" || "${PURGE_AUDITS}" == "true" || "${EXPORT_PURGE_AUDITS}" == "true" || "${ROTATE_EXPORTS}" == "true" || "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS}" == "true") ]]; then
  echo "invalid mode: --restore-effective-policy-distributions cannot be combined with verify/preflight/purge/export/rotate/list modes"
  exit 1
fi

if [[ "${RESTORE_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR}" == "true" && "${RESTORE_EFFECTIVE_POLICY_VERIFY_INTEGRITY}" != "true" ]]; then
  echo "invalid mode: --restore-effective-policy-fail-on-integrity-error requires --restore-effective-policy-verify-integrity"
  exit 1
fi

if [[ "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS}" == "true" && (-n "${RESTORE_EFFECTIVE_POLICY_REMAP_FROM}" || -n "${RESTORE_EFFECTIVE_POLICY_REMAP_TO}") ]]; then
  if [[ -z "${RESTORE_EFFECTIVE_POLICY_REMAP_FROM}" || -z "${RESTORE_EFFECTIVE_POLICY_REMAP_TO}" ]]; then
    echo "invalid mode: --restore-effective-policy-remap-from and --restore-effective-policy-remap-to must be used together"
    exit 1
  fi
fi

POLICY_PATH="${WHERECODE_METRICS_ALERT_POLICY_FILE:-${ROOT_DIR}/control_center/metrics_alert_policy.json}"
AUDIT_PATH="${WHERECODE_METRICS_ALERT_AUDIT_FILE:-${ROOT_DIR}/.wherecode/metrics_alert_policy_audit.jsonl}"
APPROVAL_PATH="${WHERECODE_METRICS_ROLLBACK_APPROVAL_FILE:-${ROOT_DIR}/.wherecode/metrics_rollback_approvals.jsonl}"
PURGE_AUDIT_PATH="${WHERECODE_METRICS_ROLLBACK_APPROVAL_PURGE_AUDIT_FILE:-${ROOT_DIR}/.wherecode/metrics_rollback_approval_purge_audit.jsonl}"
TTL_SECONDS="${WHERECODE_METRICS_ROLLBACK_APPROVAL_TTL_SECONDS:-86400}"
REQUESTED_BY="${METRICS_ROLLBACK_APPROVAL_GC_REQUESTED_BY:-ops-script}"

"${PYTHON_BIN}" - "${POLICY_PATH}" "${AUDIT_PATH}" "${APPROVAL_PATH}" "${PURGE_AUDIT_PATH}" "${TTL_SECONDS}" "${REMOVE_USED}" "${REMOVE_EXPIRED}" "${DRY_RUN}" "${OLDER_THAN_SECONDS}" "${KEEP_LATEST}" "${PURGE_AUDITS}" "${EXPORT_PURGE_AUDITS}" "${EXPORT_FROM_ISO}" "${EXPORT_TO_ISO}" "${EXPORT_EVENT_TYPE}" "${EXPORT_LIMIT}" "${EXPORT_OUTPUT_PATH}" "${ROTATE_EXPORTS}" "${ROTATE_EXPORT_DIR}" "${ROTATE_OLDER_THAN_SECONDS}" "${ROTATE_KEEP_LATEST_FILES}" "${MANIFEST_PATH}" "${VERIFY_MANIFEST}" "${VERIFY_MANIFEST_ID}" "${VERIFY_EXPORT_FILE}" "${MANIFEST_KEY_ID}" "${MANIFEST_SIGNATURE}" "${VERIFY_REPORT_OUTPUT}" "${VERIFY_REPORT_FORMAT}" "${MANIFEST_SIGNER_CMD}" "${MANIFEST_SIGNER_TIMEOUT}" "${SIGNER_PREFLIGHT}" "${PREFLIGHT_HISTORY_PATH}" "${PREFLIGHT_HISTORY_WINDOW}" "${VERIFY_TREND_WINDOW}" "${VERIFY_ARCHIVE_DIR}" "${VERIFY_FETCH_CMD}" "${VERIFY_FETCH_TIMEOUT}" "${VERIFY_ALLOWED_RESOLVERS}" "${POLICY_PROFILE}" "${POLICY_FILE_PATH}" "${POLICY_SOURCE_URL}" "${POLICY_SOURCE_TIMEOUT}" "${POLICY_SOURCE_TOKEN}" "${EXPORT_EFFECTIVE_POLICY_PATH}" "${DISTRIBUTE_EFFECTIVE_POLICY_DIR}" "${DISTRIBUTE_EFFECTIVE_POLICY_RETAIN_SECONDS}" "${DISTRIBUTE_EFFECTIVE_POLICY_KEEP_LATEST}" "${PREFLIGHT_SLO_MIN_PASS_RATE}" "${PREFLIGHT_SLO_MAX_CONSECUTIVE_FAILURES}" "${VERIFY_SLO_MIN_PASS_RATE}" "${VERIFY_SLO_MAX_FETCH_FAILURES}" "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS}" "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT}" "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_MODE}" "${LIST_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO}" "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS}" "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_LIMIT}" "${RESTORE_EFFECTIVE_POLICY_DISTRIBUTIONS_SINCE_ISO}" "${RESTORE_EFFECTIVE_POLICY_VERIFY_INTEGRITY}" "${RESTORE_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR}" "${RESTORE_EFFECTIVE_POLICY_REMAP_FROM}" "${RESTORE_EFFECTIVE_POLICY_REMAP_TO}" "${RESTORE_EFFECTIVE_POLICY_STATE_FILE}" "${RESTORE_EFFECTIVE_POLICY_MIN_RESTORED}" "${LIST_EFFECTIVE_POLICY_FAIL_ON_INTEGRITY_ERROR}" "${LIST_EFFECTIVE_POLICY_FAIL_ON_EMPTY}" "${LIST_EFFECTIVE_POLICY_MIN_SELECTED}" "${LIST_EFFECTIVE_POLICY_STATE_FILE}" "${REQUESTED_BY}" "${ROOT_DIR}/control_center/services/metrics_alert_policy_store.py" <<'PY'
from __future__ import annotations

import importlib.util
import hashlib
import json
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

policy_path = sys.argv[1]
audit_path = sys.argv[2]
approval_path = sys.argv[3]
purge_audit_path = sys.argv[4]
ttl_seconds_raw = sys.argv[5]
remove_used = sys.argv[6].lower() == "true"
remove_expired = sys.argv[7].lower() == "true"
dry_run = sys.argv[8].lower() == "true"
older_than_raw = sys.argv[9].strip()
keep_latest_raw = sys.argv[10].strip()
purge_audits = sys.argv[11].lower() == "true"
export_purge_audits = sys.argv[12].lower() == "true"
export_from_iso = sys.argv[13].strip()
export_to_iso = sys.argv[14].strip()
export_event_type = sys.argv[15].strip()
export_limit_raw = sys.argv[16].strip()
export_output_path = sys.argv[17].strip()
rotate_exports = sys.argv[18].lower() == "true"
rotate_export_dir = sys.argv[19].strip()
rotate_older_than_raw = sys.argv[20].strip()
rotate_keep_latest_raw = sys.argv[21].strip()
manifest_path_raw = sys.argv[22].strip()
verify_manifest = sys.argv[23].lower() == "true"
verify_manifest_id = sys.argv[24].strip()
verify_export_file = sys.argv[25].strip()
manifest_key_id = sys.argv[26].strip()
manifest_signature = sys.argv[27].strip()
verify_report_output = sys.argv[28].strip()
verify_report_format = sys.argv[29].strip().lower()
manifest_signer_cmd = sys.argv[30].strip()
manifest_signer_timeout_raw = sys.argv[31].strip()
signer_preflight = sys.argv[32].lower() == "true"
preflight_history_path_raw = sys.argv[33].strip()
preflight_history_window_raw = sys.argv[34].strip()
verify_trend_window_raw = sys.argv[35].strip()
verify_archive_dir_raw = sys.argv[36].strip()
verify_fetch_cmd = sys.argv[37].strip()
verify_fetch_timeout_raw = sys.argv[38].strip()
verify_allowed_resolvers_raw = sys.argv[39].strip()
policy_profile_raw = sys.argv[40].strip().lower()
policy_file_path_raw = sys.argv[41].strip()
policy_source_url_raw = sys.argv[42].strip()
policy_source_timeout_raw = sys.argv[43].strip()
policy_source_token_raw = sys.argv[44].strip()
export_effective_policy_path_raw = sys.argv[45].strip()
distribute_effective_policy_dir_raw = sys.argv[46].strip()
distribute_effective_policy_retain_seconds_raw = sys.argv[47].strip()
distribute_effective_policy_keep_latest_raw = sys.argv[48].strip()
preflight_slo_min_pass_rate_raw = sys.argv[49].strip()
preflight_slo_max_consecutive_failures_raw = sys.argv[50].strip()
verify_slo_min_pass_rate_raw = sys.argv[51].strip()
verify_slo_max_fetch_failures_raw = sys.argv[52].strip()
list_effective_policy_distributions = sys.argv[53].lower() == "true"
list_effective_policy_distributions_limit_raw = sys.argv[54].strip()
list_effective_policy_distributions_mode_raw = sys.argv[55].strip().lower()
list_effective_policy_distributions_since_iso_raw = sys.argv[56].strip()
restore_effective_policy_distributions = sys.argv[57].lower() == "true"
restore_effective_policy_distributions_limit_raw = sys.argv[58].strip()
restore_effective_policy_distributions_since_iso_raw = sys.argv[59].strip()
restore_effective_policy_verify_integrity = sys.argv[60].lower() == "true"
restore_effective_policy_fail_on_integrity_error = sys.argv[61].lower() == "true"
restore_effective_policy_remap_from_raw = sys.argv[62].strip()
restore_effective_policy_remap_to_raw = sys.argv[63].strip()
restore_effective_policy_state_file_raw = sys.argv[64].strip()
restore_effective_policy_min_restored_raw = sys.argv[65].strip()
list_effective_policy_fail_on_integrity_error = sys.argv[66].lower() == "true"
list_effective_policy_fail_on_empty = sys.argv[67].lower() == "true"
list_effective_policy_min_selected_raw = sys.argv[68].strip()
list_effective_policy_state_file_raw = sys.argv[69].strip()
requested_by = sys.argv[70].strip()
module_path = Path(sys.argv[71])

spec = importlib.util.spec_from_file_location("metrics_alert_policy_store_module", module_path)
if spec is None or spec.loader is None:
    raise SystemExit(f"failed to load module: {module_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
MetricsAlertPolicyStore = getattr(module, "MetricsAlertPolicyStore")

try:
    ttl_seconds = int(ttl_seconds_raw)
except ValueError:
    ttl_seconds = 86400
try:
    older_than_seconds = int(older_than_raw) if older_than_raw else None
except ValueError:
    raise SystemExit(f"invalid --older-than-seconds: {older_than_raw}")
try:
    keep_latest = int(keep_latest_raw)
except ValueError:
    raise SystemExit(f"invalid --keep-latest: {keep_latest_raw}")
if keep_latest < 0:
    keep_latest = 0
try:
    export_limit = int(export_limit_raw)
except ValueError:
    raise SystemExit(f"invalid --limit: {export_limit_raw}")
if export_limit < 1:
    export_limit = 1
try:
    rotate_keep_latest = int(rotate_keep_latest_raw)
except ValueError:
    raise SystemExit(f"invalid --keep-export-latest: {rotate_keep_latest_raw}")
if rotate_keep_latest < 0:
    rotate_keep_latest = 0
try:
    rotate_older_than_seconds = int(rotate_older_than_raw) if rotate_older_than_raw else None
except ValueError:
    raise SystemExit(f"invalid --retain-seconds: {rotate_older_than_raw}")
try:
    manifest_signer_timeout = int(manifest_signer_timeout_raw)
except ValueError:
    raise SystemExit(f"invalid --manifest-signer-timeout: {manifest_signer_timeout_raw}")
if manifest_signer_timeout < 1:
    manifest_signer_timeout = 1
if verify_report_format not in {"txt", "json"}:
    raise SystemExit(f"invalid --verify-report-format: {verify_report_format}")
try:
    verify_trend_window = int(verify_trend_window_raw)
except ValueError:
    raise SystemExit(f"invalid --verify-trend-window: {verify_trend_window_raw}")
if verify_trend_window < 1:
    verify_trend_window = 1
try:
    preflight_history_window = int(preflight_history_window_raw)
except ValueError:
    raise SystemExit(f"invalid --preflight-history-window: {preflight_history_window_raw}")
if preflight_history_window < 1:
    preflight_history_window = 1
verify_archive_dir = Path(verify_archive_dir_raw) if verify_archive_dir_raw else None
try:
    verify_fetch_timeout = int(verify_fetch_timeout_raw)
except ValueError:
    raise SystemExit(f"invalid --verify-fetch-timeout: {verify_fetch_timeout_raw}")
if verify_fetch_timeout < 1:
    verify_fetch_timeout = 1
try:
    policy_source_timeout = int(policy_source_timeout_raw)
except ValueError:
    raise SystemExit(f"invalid --policy-source-timeout: {policy_source_timeout_raw}")
if policy_source_timeout < 1:
    raise SystemExit("invalid --policy-source-timeout: must be >= 1")
try:
    distribute_effective_policy_retain_seconds = (
        int(distribute_effective_policy_retain_seconds_raw)
        if distribute_effective_policy_retain_seconds_raw
        else None
    )
except ValueError:
    raise SystemExit(
        "invalid --distribute-effective-policy-retain-seconds: "
        f"{distribute_effective_policy_retain_seconds_raw}"
    )
if (
    distribute_effective_policy_retain_seconds is not None
    and distribute_effective_policy_retain_seconds < 0
):
    raise SystemExit("invalid --distribute-effective-policy-retain-seconds: must be >= 0")
try:
    distribute_effective_policy_keep_latest = (
        int(distribute_effective_policy_keep_latest_raw)
        if distribute_effective_policy_keep_latest_raw
        else None
    )
except ValueError:
    raise SystemExit(
        "invalid --distribute-effective-policy-keep-latest: "
        f"{distribute_effective_policy_keep_latest_raw}"
    )
if (
    distribute_effective_policy_keep_latest is not None
    and distribute_effective_policy_keep_latest < 0
):
    raise SystemExit("invalid --distribute-effective-policy-keep-latest: must be >= 0")
try:
    list_effective_policy_distributions_limit = int(
        list_effective_policy_distributions_limit_raw
    )
except ValueError:
    raise SystemExit(
        "invalid --list-effective-policy-distributions-limit: "
        f"{list_effective_policy_distributions_limit_raw}"
    )
if list_effective_policy_distributions_limit < 1:
    list_effective_policy_distributions_limit = 1
if list_effective_policy_distributions_mode_raw not in {"", "verify_manifest", "signer_preflight"}:
    raise SystemExit(
        "invalid --list-effective-policy-distributions-mode: "
        f"{list_effective_policy_distributions_mode_raw}"
    )
try:
    restore_effective_policy_distributions_limit = int(
        restore_effective_policy_distributions_limit_raw
    )
except ValueError:
    raise SystemExit(
        "invalid --restore-effective-policy-distributions-limit: "
        f"{restore_effective_policy_distributions_limit_raw}"
    )
if restore_effective_policy_distributions_limit < 1:
    restore_effective_policy_distributions_limit = 1


def parse_optional_float(name: str, raw: str) -> float | None:
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid {name}: {raw}") from exc
    return value


def parse_optional_int(name: str, raw: str) -> int | None:
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"invalid {name}: {raw}") from exc
    return value


preflight_slo_min_pass_rate = parse_optional_float(
    "--preflight-slo-min-pass-rate",
    preflight_slo_min_pass_rate_raw,
)
preflight_slo_max_consecutive_failures = parse_optional_int(
    "--preflight-slo-max-consecutive-failures",
    preflight_slo_max_consecutive_failures_raw,
)
verify_slo_min_pass_rate = parse_optional_float(
    "--verify-slo-min-pass-rate",
    verify_slo_min_pass_rate_raw,
)
verify_slo_max_fetch_failures = parse_optional_int(
    "--verify-slo-max-fetch-failures",
    verify_slo_max_fetch_failures_raw,
)
list_effective_policy_min_selected = parse_optional_int(
    "--list-effective-policy-min-selected",
    list_effective_policy_min_selected_raw,
)
if (
    list_effective_policy_min_selected is not None
    and list_effective_policy_min_selected < 0
):
    raise SystemExit("invalid --list-effective-policy-min-selected: must be >= 0")
restore_effective_policy_min_restored = parse_optional_int(
    "--restore-effective-policy-min-restored",
    restore_effective_policy_min_restored_raw,
)
if (
    restore_effective_policy_min_restored is not None
    and restore_effective_policy_min_restored < 0
):
    raise SystemExit("invalid --restore-effective-policy-min-restored: must be >= 0")
policy_file_path = Path(policy_file_path_raw) if policy_file_path_raw else None
policy_source_url = policy_source_url_raw
policy_source_token = policy_source_token_raw
export_effective_policy_path = (
    Path(export_effective_policy_path_raw)
    if export_effective_policy_path_raw
    else None
)
distribute_effective_policy_dir = (
    Path(distribute_effective_policy_dir_raw)
    if distribute_effective_policy_dir_raw
    else None
)
distribute_effective_policy_cleanup_enabled = (
    distribute_effective_policy_keep_latest is not None
    or distribute_effective_policy_retain_seconds is not None
)
distribute_effective_policy_keep_latest_value = (
    int(distribute_effective_policy_keep_latest or 0)
)


def parse_policy_payload(
    payload: dict[str, object],
    *,
    source_label: str,
) -> tuple[str, dict[str, dict[str, object]]]:
    default_profile = str(payload.get("default_profile", "")).strip().lower()
    profiles: dict[str, dict[str, object]] = {}
    profiles_payload = payload.get("profiles")
    if profiles_payload is None:
        return default_profile, profiles
    if not isinstance(profiles_payload, dict):
        raise SystemExit(f"invalid policy profiles payload: {source_label}")
    for key, value in profiles_payload.items():
        profile_name = str(key).strip().lower()
        if not profile_name:
            continue
        if not isinstance(value, dict):
            raise SystemExit(f"invalid profile config in policy source: {profile_name}")
        profile_entry: dict[str, object] = {}
        if "allowed_resolvers" in value:
            allowed_value = value.get("allowed_resolvers")
            if isinstance(allowed_value, list):
                profile_entry["allowed_resolvers"] = {
                    str(item).strip()
                    for item in allowed_value
                    if str(item).strip()
                }
            else:
                raise SystemExit(f"invalid allowed_resolvers in profile: {profile_name}")
        for field in (
            "preflight_slo_min_pass_rate",
            "preflight_slo_max_consecutive_failures",
            "verify_slo_min_pass_rate",
            "verify_slo_max_fetch_failures",
        ):
            if field in value:
                profile_entry[field] = value[field]
        profiles[profile_name] = profile_entry
    return default_profile, profiles


def load_policy_payload_from_file(path: Path, *, cli_name: str) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"policy file missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid {cli_name} json: {path}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid {cli_name} payload: {path}")
    return payload


def load_policy_payload_from_url(
    *,
    source_url: str,
    timeout_seconds: int,
    token: str,
) -> dict[str, object]:
    parsed = urlparse(source_url)
    if parsed.scheme in {"", "file"}:
        if parsed.scheme == "file":
            file_path = Path(unquote(parsed.path or ""))
            if not file_path and parsed.netloc:
                file_path = Path(unquote(parsed.netloc))
        else:
            file_path = Path(source_url)
        return load_policy_payload_from_file(file_path, cli_name="--policy-source-url")

    headers = {"Accept": "application/json"}
    if token:
        headers["X-WhereCode-Token"] = token
    request = Request(source_url, headers=headers)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except (URLError, HTTPError, TimeoutError) as exc:
        raise SystemExit(f"failed to fetch --policy-source-url: {source_url}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --policy-source-url json: {source_url}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid --policy-source-url payload: {source_url}")
    return payload


policy_source_kind = "builtin"
policy_source_descriptor = ""
policy_source_default_profile = ""
policy_source_profiles: dict[str, dict[str, object]] = {}
if policy_file_path is not None:
    policy_source_kind = "policy_file"
    policy_source_descriptor = str(policy_file_path)
    policy_payload = load_policy_payload_from_file(policy_file_path, cli_name="--policy-file")
    policy_source_default_profile, policy_source_profiles = parse_policy_payload(
        policy_payload,
        source_label=policy_source_descriptor,
    )
elif policy_source_url:
    policy_source_kind = "policy_url"
    policy_source_descriptor = policy_source_url
    policy_payload = load_policy_payload_from_url(
        source_url=policy_source_url,
        timeout_seconds=policy_source_timeout,
        token=policy_source_token,
    )
    policy_source_default_profile, policy_source_profiles = parse_policy_payload(
        policy_payload,
        source_label=policy_source_descriptor,
    )

policy_profile = policy_profile_raw or policy_source_default_profile or "custom"
profile_defaults = {
    "custom": {},
    "strict": {
        "allowed_resolvers": {
            "manifest_output_path",
            "manifest_file_uri",
            "archive_basename_fallback",
        },
        "preflight_slo_min_pass_rate": 1.0,
        "preflight_slo_max_consecutive_failures": 0,
        "verify_slo_min_pass_rate": 1.0,
        "verify_slo_max_fetch_failures": 0,
    },
    "standard": {
        "allowed_resolvers": {
            "manifest_output_path",
            "manifest_file_uri",
            "archive_basename_fallback",
            "archive_relative_fallback",
            "fetch_hook",
        },
        "preflight_slo_min_pass_rate": 0.95,
        "preflight_slo_max_consecutive_failures": 1,
        "verify_slo_min_pass_rate": 0.9,
        "verify_slo_max_fetch_failures": 1,
    },
    "degraded": {
        "allowed_resolvers": {
            "manifest_output_path",
            "manifest_file_uri",
            "archive_basename_fallback",
            "archive_relative_fallback",
            "fetch_hook",
        },
        "preflight_slo_min_pass_rate": 0.8,
        "preflight_slo_max_consecutive_failures": 3,
        "verify_slo_min_pass_rate": 0.7,
        "verify_slo_max_fetch_failures": 5,
    },
}
if policy_source_profiles:
    for name, profile in policy_source_profiles.items():
        base = dict(profile_defaults.get(name, {}))
        base.update(profile)
        profile_defaults[name] = base
if policy_profile not in profile_defaults:
    raise SystemExit(f"invalid --policy-profile: {policy_profile_raw}")
profile = profile_defaults[policy_profile]

if signer_preflight and policy_profile != "custom" and not preflight_history_path_raw:
    raise SystemExit("invalid mode: non-custom --policy-profile in preflight mode requires --preflight-history")

if preflight_slo_min_pass_rate is None:
    preflight_slo_min_pass_rate = profile.get("preflight_slo_min_pass_rate")
if preflight_slo_max_consecutive_failures is None:
    preflight_slo_max_consecutive_failures = profile.get("preflight_slo_max_consecutive_failures")
if verify_slo_min_pass_rate is None:
    verify_slo_min_pass_rate = profile.get("verify_slo_min_pass_rate")
if verify_slo_max_fetch_failures is None:
    verify_slo_max_fetch_failures = profile.get("verify_slo_max_fetch_failures")

if preflight_slo_min_pass_rate is not None:
    try:
        preflight_slo_min_pass_rate = float(preflight_slo_min_pass_rate)
    except (TypeError, ValueError) as exc:
        raise SystemExit("invalid --preflight-slo-min-pass-rate value in profile") from exc
if verify_slo_min_pass_rate is not None:
    try:
        verify_slo_min_pass_rate = float(verify_slo_min_pass_rate)
    except (TypeError, ValueError) as exc:
        raise SystemExit("invalid --verify-slo-min-pass-rate value in profile") from exc
if preflight_slo_max_consecutive_failures is not None:
    try:
        preflight_slo_max_consecutive_failures = int(preflight_slo_max_consecutive_failures)
    except (TypeError, ValueError) as exc:
        raise SystemExit("invalid --preflight-slo-max-consecutive-failures value in profile") from exc
if verify_slo_max_fetch_failures is not None:
    try:
        verify_slo_max_fetch_failures = int(verify_slo_max_fetch_failures)
    except (TypeError, ValueError) as exc:
        raise SystemExit("invalid --verify-slo-max-fetch-failures value in profile") from exc

if preflight_slo_min_pass_rate is not None and not (0.0 <= preflight_slo_min_pass_rate <= 1.0):
    raise SystemExit("invalid --preflight-slo-min-pass-rate: must be between 0 and 1")
if verify_slo_min_pass_rate is not None and not (0.0 <= verify_slo_min_pass_rate <= 1.0):
    raise SystemExit("invalid --verify-slo-min-pass-rate: must be between 0 and 1")
if preflight_slo_max_consecutive_failures is not None and preflight_slo_max_consecutive_failures < 0:
    raise SystemExit("invalid --preflight-slo-max-consecutive-failures: must be >= 0")
if verify_slo_max_fetch_failures is not None and verify_slo_max_fetch_failures < 0:
    raise SystemExit("invalid --verify-slo-max-fetch-failures: must be >= 0")

valid_resolvers = {
    "manifest_output_path",
    "manifest_file_uri",
    "archive_basename_fallback",
    "archive_relative_fallback",
    "fetch_hook",
}
allowed_resolvers_cli = {
    item.strip()
    for item in verify_allowed_resolvers_raw.split(",")
    if item.strip()
}
if allowed_resolvers_cli:
    invalid_resolvers = sorted(allowed_resolvers_cli - valid_resolvers)
    if invalid_resolvers:
        raise SystemExit(
            f"invalid --verify-allowed-resolvers: {','.join(invalid_resolvers)}"
        )
    allowed_resolvers = allowed_resolvers_cli
else:
    defaults = profile.get("allowed_resolvers")
    allowed_resolvers = set(defaults) if defaults else None

if allowed_resolvers is not None:
    invalid_resolvers = sorted(allowed_resolvers - valid_resolvers)
    if invalid_resolvers:
        raise SystemExit(
            f"invalid allowed_resolvers in effective policy: {','.join(invalid_resolvers)}"
        )

effective_policy = {
    "policy_profile": policy_profile,
    "policy_file": str(policy_file_path) if policy_file_path is not None else None,
    "policy_source_url": policy_source_url or None,
    "policy_source_timeout": policy_source_timeout if policy_source_url else None,
    "policy_source": policy_source_kind,
    "policy_source_descriptor": policy_source_descriptor or None,
    "allowed_resolvers": sorted(allowed_resolvers) if allowed_resolvers is not None else None,
    "preflight_slo_min_pass_rate": preflight_slo_min_pass_rate,
    "preflight_slo_max_consecutive_failures": preflight_slo_max_consecutive_failures,
    "verify_slo_min_pass_rate": verify_slo_min_pass_rate,
    "verify_slo_max_fetch_failures": verify_slo_max_fetch_failures,
}

def parse_iso(raw: str):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"invalid iso datetime: {raw}") from exc


list_effective_policy_distributions_since = parse_iso(
    list_effective_policy_distributions_since_iso_raw
)
restore_effective_policy_distributions_since = parse_iso(
    restore_effective_policy_distributions_since_iso_raw
)
restore_effective_policy_remap_from = restore_effective_policy_remap_from_raw
restore_effective_policy_remap_to = restore_effective_policy_remap_to_raw
restore_effective_policy_state_file = (
    Path(restore_effective_policy_state_file_raw)
    if restore_effective_policy_state_file_raw
    else None
)
list_effective_policy_state_file = (
    Path(list_effective_policy_state_file_raw)
    if list_effective_policy_state_file_raw
    else None
)


def load_manifest_entries(manifest_path: Path) -> list[dict[str, object]]:
    if not manifest_path.exists():
        return []
    entries: list[dict[str, object]] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            continue
        entries.append(payload)
    return entries


def compute_entries_checksum(entries) -> str:
    return hashlib.sha256(
        json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def compact_distribution_index(
    *,
    index_path: Path,
    max_entries: int,
    archive_path: Path,
) -> dict[str, int | str]:
    entries = load_jsonl_entries(index_path)
    total_before = len(entries)
    if total_before <= max_entries:
        return {
            "total_before": total_before,
            "total_after": total_before,
            "removed_total": 0,
            "archive_path": str(archive_path),
            "archived_total": 0,
        }
    entries.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    kept = entries[:max_entries]
    removed = entries[max_entries:]
    kept.reverse()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in kept) + "\n",
        encoding="utf-8",
    )
    archived_total = 0
    for item in removed:
        archived = dict(item)
        archived["archived_at"] = datetime.now().astimezone().isoformat()
        archived["archive_reason"] = "index_compaction"
        append_jsonl_entry(archive_path, archived)
        archived_total += 1
    return {
        "total_before": total_before,
        "total_after": len(kept),
        "removed_total": total_before - len(kept),
        "archive_path": str(archive_path),
        "archived_total": archived_total,
    }


def run_signer_hook(
    *,
    signer_cmd: str,
    timeout_seconds: int,
    payload: dict[str, object],
) -> dict[str, str]:
    command = shlex.split(signer_cmd)
    if not command:
        raise SystemExit("invalid --manifest-signer-cmd: empty command")
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"manifest signer timeout after {timeout_seconds}s: {signer_cmd}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise SystemExit(
            f"manifest signer failed (code={exc.returncode}): {stderr or signer_cmd}"
        ) from exc

    raw = (completed.stdout or "").strip()
    if not raw:
        raise SystemExit("manifest signer returned empty output")
    try:
        signer_output = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"manifest signer output is not json: {raw}") from exc
    if not isinstance(signer_output, dict):
        raise SystemExit("manifest signer output must be json object")
    key_id = str(signer_output.get("key_id", "")).strip()
    signature = str(signer_output.get("signature", "")).strip()
    if not key_id or not signature:
        raise SystemExit("manifest signer output missing key_id/signature")
    return {"key_id": key_id, "signature": signature}


def load_jsonl_entries(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    entries: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def append_jsonl_entry(path: Path, entry: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_state_snapshot(path: Path, payload: dict[str, object]) -> None:
    if not isinstance(payload, dict):
        raise SystemExit("invalid state payload: expected json object")
    merged_payload = dict(payload)
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        if raw.strip():
            try:
                existing_payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid state-file json: {path}") from exc
            if not isinstance(existing_payload, dict):
                raise SystemExit(f"invalid state-file payload: {path}")
            merged_payload = dict(existing_payload)
            merged_payload.update(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(merged_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_effective_policy_snapshot(
    *,
    output_path: Path,
    mode: str,
    effective_policy_payload: dict[str, object],
) -> None:
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "mode": mode,
        "effective_policy": effective_policy_payload,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def distribute_effective_policy_snapshot(
    *,
    output_dir: Path,
    mode: str,
    effective_policy_payload: dict[str, object],
    cleanup_enabled: bool,
    retain_seconds: int | None,
    keep_latest: int,
) -> dict[str, object]:
    distribution_index_max_entries = 500
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z")
    versioned_path = output_dir / f"effective_policy_{mode}_{timestamp}.json"
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "mode": mode,
        "effective_policy": effective_policy_payload,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    versioned_path.write_text(content, encoding="utf-8")
    latest_path = output_dir / "latest.json"
    latest_path.write_text(content, encoding="utf-8")
    versioned_checksum_sha256 = compute_file_sha256(versioned_path)

    removed_paths: list[str] = []
    kept_paths: list[str] = []
    versioned_files = sorted(
        [
            item
            for item in output_dir.glob("effective_policy_*.json")
            if item.is_file()
        ],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if cleanup_enabled:
        now_timestamp = datetime.now().astimezone().timestamp()
        for index, file_path in enumerate(versioned_files):
            if file_path == versioned_path:
                kept_paths.append(str(file_path))
                continue
            if index < keep_latest:
                kept_paths.append(str(file_path))
                continue
            if retain_seconds is not None:
                age_seconds = now_timestamp - file_path.stat().st_mtime
                if age_seconds < retain_seconds:
                    kept_paths.append(str(file_path))
                    continue
            file_path.unlink(missing_ok=True)
            removed_paths.append(str(file_path))
    else:
        kept_paths = [str(item) for item in versioned_files]

    remaining_versioned = sorted(
        [
            item
            for item in output_dir.glob("effective_policy_*.json")
            if item.is_file()
        ],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    index_path = output_dir / "distribution-index.jsonl"
    index_entry = {
        "id": f"dist_{int(datetime.now().astimezone().timestamp() * 1000)}",
        "created_at": datetime.now().astimezone().isoformat(),
        "mode": mode,
        "versioned_path": str(versioned_path),
        "versioned_checksum_sha256": versioned_checksum_sha256,
        "latest_path": str(latest_path),
        "policy_profile": str(effective_policy_payload.get("policy_profile", "")).strip() or None,
        "policy_source": str(effective_policy_payload.get("policy_source", "")).strip() or None,
        "cleanup_enabled": cleanup_enabled,
        "retain_seconds": retain_seconds,
        "keep_latest": keep_latest,
        "removed_total": len(removed_paths),
        "remaining_versioned_total": len(remaining_versioned),
    }
    append_jsonl_entry(index_path, index_entry)
    archive_path = output_dir / "distribution-index-archive.jsonl"
    compaction_result = compact_distribution_index(
        index_path=index_path,
        max_entries=distribution_index_max_entries,
        archive_path=archive_path,
    )
    return {
        "versioned_path": str(versioned_path),
        "versioned_checksum_sha256": versioned_checksum_sha256,
        "latest_path": str(latest_path),
        "index_path": str(index_path),
        "index_entry_id": str(index_entry["id"]),
        "index_compaction_max_entries": distribution_index_max_entries,
        "index_compaction_removed_total": int(compaction_result["removed_total"]),
        "index_total_after_compaction": int(compaction_result["total_after"]),
        "index_archive_path": str(compaction_result["archive_path"]),
        "index_archive_appended_total": int(compaction_result["archived_total"]),
        "cleanup_enabled": cleanup_enabled,
        "retain_seconds": retain_seconds,
        "keep_latest": keep_latest,
        "removed_total": len(removed_paths),
        "remaining_versioned_total": len(remaining_versioned),
        "removed_paths": removed_paths[:50],
        "kept_paths": kept_paths[:50],
    }


def list_effective_policy_distribution_index(
    *,
    output_dir: Path,
    limit: int,
    mode_filter: str | None,
    since_at,
) -> dict[str, object]:
    index_path = output_dir / "distribution-index.jsonl"
    entries = load_jsonl_entries(index_path)

    filtered: list[dict[str, object]] = []
    for entry in entries:
        mode_value = str(entry.get("mode", "")).strip().lower()
        if mode_filter and mode_value != mode_filter:
            continue
        if since_at is not None:
            created_raw = str(entry.get("created_at", "")).strip()
            if not created_raw:
                continue
            try:
                created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            if created_at < since_at:
                continue
        filtered.append(entry)

    filtered.sort(
        key=lambda item: str(item.get("created_at", "")),
        reverse=True,
    )
    limited = filtered[:limit]
    enriched_entries: list[dict[str, object]] = []
    integrity_checked_total = 0
    integrity_failed_total = 0
    for entry in limited:
        enriched = dict(entry)
        expected_checksum = str(enriched.get("versioned_checksum_sha256", "")).strip()
        versioned_path_raw = str(enriched.get("versioned_path", "")).strip()
        if not expected_checksum:
            enriched["integrity_status"] = "checksum_missing"
            enriched["integrity_ok"] = False
            integrity_failed_total += 1
        elif not versioned_path_raw:
            enriched["integrity_status"] = "versioned_path_missing"
            enriched["integrity_ok"] = False
            integrity_failed_total += 1
        else:
            integrity_checked_total += 1
            versioned_path = Path(versioned_path_raw)
            if not versioned_path.exists():
                enriched["integrity_status"] = "versioned_file_missing"
                enriched["integrity_ok"] = False
                integrity_failed_total += 1
            else:
                actual_checksum = compute_file_sha256(versioned_path)
                enriched["actual_versioned_checksum_sha256"] = actual_checksum
                if actual_checksum == expected_checksum:
                    enriched["integrity_status"] = "ok"
                    enriched["integrity_ok"] = True
                else:
                    enriched["integrity_status"] = "checksum_mismatch"
                    enriched["integrity_ok"] = False
                    integrity_failed_total += 1
        enriched_entries.append(enriched)
    selected_total = len(limited)
    integrity_guard_passed = integrity_failed_total == 0
    if selected_total == 0:
        risk_level = "medium"
    elif integrity_failed_total == 0:
        risk_level = "low"
    elif integrity_checked_total == 0:
        risk_level = "high"
    elif (integrity_failed_total / selected_total) >= 0.5:
        risk_level = "high"
    else:
        risk_level = "medium"

    recommendations: list[str] = []
    if len(filtered) == 0:
        recommendations.append(
            "adjust list mode/since filters to include distribution entries"
        )
    if integrity_failed_total > 0:
        recommendations.append(
            "inspect entries[].integrity_status and rebuild mismatched distribution artifacts"
        )
        recommendations.append(
            "enable --list-effective-policy-fail-on-integrity-error for ci gate"
        )

    if selected_total == 0:
        summary = "list completed: no entries matched filters"
    elif integrity_failed_total == 0:
        summary = f"list completed: {selected_total} entries passed integrity guard"
    else:
        summary = f"list completed: {integrity_failed_total} entries failed integrity guard"

    return {
        "distribution_dir": str(output_dir),
        "distribution_index_path": str(index_path),
        "limit": limit,
        "mode_filter": mode_filter,
        "since_iso": since_at.isoformat() if since_at is not None else None,
        "scanned_total": len(entries),
        "matched_total": len(filtered),
        "selected_total": selected_total,
        "integrity_checked_total": integrity_checked_total,
        "integrity_failed_total": integrity_failed_total,
        "integrity_guard_passed": integrity_guard_passed,
        "list_safety_risk_level": risk_level,
        "list_recommendations": recommendations[:10],
        "summary": summary,
        "entries": enriched_entries,
    }


def restore_effective_policy_distribution_index(
    *,
    output_dir: Path,
    limit: int,
    since_at,
    dry_run: bool,
    verify_integrity: bool,
    fail_on_integrity_error: bool,
    remap_from: str,
    remap_to: str,
) -> dict[str, object]:
    index_path = output_dir / "distribution-index.jsonl"
    archive_path = output_dir / "distribution-index-archive.jsonl"
    index_entries = load_jsonl_entries(index_path)
    archive_entries = load_jsonl_entries(archive_path)

    existing_ids = {
        str(item.get("id", "")).strip()
        for item in index_entries
        if str(item.get("id", "")).strip()
    }

    filtered: list[dict[str, object]] = []
    for entry in archive_entries:
        if since_at is not None:
            time_raw = (
                str(entry.get("archived_at", "")).strip()
                or str(entry.get("created_at", "")).strip()
            )
            if not time_raw:
                continue
            try:
                candidate_time = datetime.fromisoformat(time_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            if candidate_time < since_at:
                continue
        filtered.append(entry)

    filtered.sort(
        key=lambda item: (
            str(item.get("archived_at", "")).strip()
            or str(item.get("created_at", "")).strip()
        ),
        reverse=True,
    )
    candidates = filtered[:limit]

    restore_candidate_ids: list[str] = []
    for entry in candidates:
        entry_id = str(entry.get("id", "")).strip()
        if entry_id:
            restore_candidate_ids.append(entry_id)

    integrity_checked_total = 0
    integrity_failed_total = 0
    restore_skipped_integrity_total = 0
    integrity_failed_ids: list[str] = []
    restore_path_remap_applied_total = 0
    restore_path_remap_applied_ids: list[str] = []

    restored_total = 0
    would_restore_total = 0
    skipped_existing_total = 0
    restored_ids: list[str] = []
    would_restore_ids: list[str] = []
    skipped_existing_ids: list[str] = []

    def remap_versioned_path(raw_path: str) -> tuple[str, bool]:
        if not remap_from or not remap_to:
            return raw_path, False
        from_prefix = remap_from.rstrip("/")
        to_prefix = remap_to.rstrip("/")
        if not from_prefix:
            return raw_path, False
        if raw_path == remap_from or raw_path == from_prefix:
            return remap_to, True
        if raw_path.startswith(from_prefix + "/"):
            return to_prefix + raw_path[len(from_prefix) :], True
        return raw_path, False

    for entry in reversed(candidates):
        entry_id = str(entry.get("id", "")).strip()
        if entry_id and entry_id in existing_ids:
            skipped_existing_total += 1
            if entry_id:
                skipped_existing_ids.append(entry_id)
            continue

        versioned_path_raw = str(entry.get("versioned_path", "")).strip()
        remapped_versioned_path_raw, remap_applied = remap_versioned_path(versioned_path_raw)
        if remap_applied:
            restore_path_remap_applied_total += 1
            if entry_id:
                restore_path_remap_applied_ids.append(entry_id)

        if verify_integrity:
            expected_checksum = str(entry.get("versioned_checksum_sha256", "")).strip()
            integrity_ok = False
            if expected_checksum and remapped_versioned_path_raw:
                integrity_checked_total += 1
                versioned_path = Path(remapped_versioned_path_raw)
                if versioned_path.exists():
                    actual_checksum = compute_file_sha256(versioned_path)
                    integrity_ok = actual_checksum == expected_checksum
            if not integrity_ok:
                integrity_failed_total += 1
                restore_skipped_integrity_total += 1
                if entry_id:
                    integrity_failed_ids.append(entry_id)
                continue
        would_restore_total += 1
        if entry_id:
            would_restore_ids.append(entry_id)
        if dry_run:
            continue
        restored = dict(entry)
        restored.pop("archived_at", None)
        restored.pop("archive_reason", None)
        if remap_applied:
            restored["versioned_path"] = remapped_versioned_path_raw
        append_jsonl_entry(index_path, restored)
        if entry_id:
            existing_ids.add(entry_id)
            restored_ids.append(entry_id)
        index_entries.append(restored)
        restored_total += 1

    if dry_run:
        risk_level = "low"
    elif would_restore_total > 0 and not verify_integrity:
        risk_level = "high"
    elif integrity_failed_total > 0 and not fail_on_integrity_error:
        risk_level = "medium"
    else:
        risk_level = "low"

    recommendations: list[str] = []
    if dry_run and would_restore_total > 0:
        recommendations.append(
            "remove --dry-run to apply restore writes after review"
        )
    if not verify_integrity and would_restore_total > 0:
        recommendations.append(
            "enable --restore-effective-policy-verify-integrity before applying restore"
        )
    if verify_integrity and integrity_failed_total > 0 and not fail_on_integrity_error:
        recommendations.append(
            "enable --restore-effective-policy-fail-on-integrity-error for non-zero gate"
        )
    if remap_from and remap_to and restore_path_remap_applied_total == 0:
        recommendations.append(
            "check --restore-effective-policy-remap-from/--restore-effective-policy-remap-to values"
        )
    if not dry_run and restored_total == 0 and len(candidates) > 0:
        recommendations.append(
            "adjust restore since/limit filters to include restorable entries"
        )

    if dry_run:
        summary = f"restore dry-run completed: {would_restore_total} entries would be restored"
    elif restored_total > 0:
        summary = f"restore completed: restored {restored_total} entries"
    else:
        summary = "restore completed: no entries restored"

    return {
        "dry_run": dry_run,
        "restore_integrity_check_enabled": verify_integrity,
        "restore_integrity_fail_on_error": fail_on_integrity_error,
        "restore_path_remap_enabled": bool(remap_from or remap_to),
        "restore_path_remap_from": remap_from or None,
        "restore_path_remap_to": remap_to or None,
        "distribution_dir": str(output_dir),
        "distribution_index_path": str(index_path),
        "distribution_archive_path": str(archive_path),
        "limit": limit,
        "since_iso": since_at.isoformat() if since_at is not None else None,
        "archive_scanned_total": len(archive_entries),
        "restore_candidate_total": len(candidates),
        "restore_candidate_ids": restore_candidate_ids[:50],
        "integrity_checked_total": integrity_checked_total,
        "integrity_failed_total": integrity_failed_total,
        "integrity_failed_ids": integrity_failed_ids[:50],
        "integrity_guard_passed": integrity_failed_total == 0,
        "restore_skipped_integrity_total": restore_skipped_integrity_total,
        "restore_path_remap_applied_total": restore_path_remap_applied_total,
        "restore_path_remap_applied_ids": restore_path_remap_applied_ids[:50],
        "would_restore_total": would_restore_total,
        "would_restore_ids": would_restore_ids[:50],
        "restored_total": restored_total,
        "restored_ids": restored_ids[:50],
        "skipped_existing_total": skipped_existing_total,
        "skipped_existing_ids": skipped_existing_ids[:50],
        "index_total_after_restore": len(index_entries),
        "restore_safety_risk_level": risk_level,
        "restore_recommendations": recommendations[:10],
        "summary": summary,
    }


def build_preflight_history_trend(
    *,
    history_entries: list[dict[str, object]],
    window_size: int,
) -> dict[str, object]:
    recent_entries = history_entries[-window_size:]
    sample_size = len(recent_entries)
    passed_total = sum(1 for item in recent_entries if bool(item.get("success")))
    failed_total = sample_size - passed_total
    pass_rate = round(passed_total / sample_size, 4) if sample_size else None
    consecutive_failures = 0
    for item in reversed(recent_entries):
        if bool(item.get("success")):
            break
        consecutive_failures += 1
    return {
        "window_size": window_size,
        "sample_size": sample_size,
        "passed_total": passed_total,
        "failed_total": failed_total,
        "pass_rate": pass_rate,
        "consecutive_failures": consecutive_failures,
    }


def run_verify_fetch_hook(
    *,
    fetch_cmd: str,
    timeout_seconds: int,
    uri: str,
) -> tuple[Path | None, str]:
    command = shlex.split(fetch_cmd)
    if not command:
        return None, "verify fetch cmd is empty"
    payload = {"uri": uri}
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
        )
    except subprocess.TimeoutExpired:
        return None, f"verify fetch timeout after {timeout_seconds}s"
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        return None, f"verify fetch failed (code={exc.returncode}): {stderr or fetch_cmd}"

    raw = (completed.stdout or "").strip()
    if not raw:
        return None, "verify fetch returned empty output"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, f"verify fetch output is not json: {raw}"
    if not isinstance(payload, dict):
        return None, "verify fetch output must be json object"
    local_path_raw = str(payload.get("local_path", "")).strip()
    if not local_path_raw:
        return None, "verify fetch output missing local_path"
    local_path = Path(local_path_raw)
    if not local_path.exists():
        return None, f"verify fetch local_path missing: {local_path}"
    return local_path, ""


def resolve_output_path(
    *,
    output_path_raw: str,
    archive_dir: Path | None,
    fetch_cmd: str,
    fetch_timeout: int,
) -> tuple[Path | None, str, str | None]:
    raw = output_path_raw.strip()
    if not raw:
        return None, "missing_output_path", None

    candidates: list[tuple[Path, str]] = []
    if raw.startswith("file://"):
        parsed = urlparse(raw)
        file_path = unquote(parsed.path or "")
        if file_path:
            candidates.append((Path(file_path), "manifest_file_uri"))
    else:
        candidates.append((Path(raw), "manifest_output_path"))

    if archive_dir is not None:
        raw_path = Path(raw)
        if raw_path.name:
            candidates.append((archive_dir / raw_path.name, "archive_basename_fallback"))
        if not raw.startswith("file://"):
            candidates.append((archive_dir / raw, "archive_relative_fallback"))

    for candidate_path, source in candidates:
        if candidate_path.exists():
            return candidate_path, source, None

    if fetch_cmd:
        fetched_path, fetch_error = run_verify_fetch_hook(
            fetch_cmd=fetch_cmd,
            timeout_seconds=fetch_timeout,
            uri=raw,
        )
        if fetched_path is not None:
            return fetched_path, "fetch_hook", None
        return None, "fetch_hook_failed", fetch_error or "unknown fetch hook error"

    return None, "path_not_found", None


def verify_manifest_entry(
    entry: dict[str, object],
    *,
    override_output_path: str | None = None,
    archive_dir: Path | None = None,
    fetch_cmd: str = "",
    fetch_timeout: int = 15,
    allowed_resolvers: set[str] | None = None,
) -> dict[str, object]:
    output_path_raw = (override_output_path or "").strip() or str(entry.get("output_path", "")).strip()
    if not output_path_raw:
        return {
            "verified": False,
            "error": "manifest entry has no output_path",
            "output_path": None,
            "resolved_from": None,
            "fetch_error": None,
            "expected_checksum": str(entry.get("checksum_sha256", "")).strip() or None,
            "actual_checksum": None,
            "embedded_checksum": None,
        }
    output_path, resolved_from, fetch_error = resolve_output_path(
        output_path_raw=output_path_raw,
        archive_dir=archive_dir,
        fetch_cmd=fetch_cmd,
        fetch_timeout=fetch_timeout,
    )
    if output_path is None:
        return {
            "verified": False,
            "error": f"export file missing: {output_path_raw}",
            "output_path": output_path_raw,
            "resolved_from": resolved_from,
            "fetch_error": fetch_error,
            "expected_checksum": str(entry.get("checksum_sha256", "")).strip() or None,
            "actual_checksum": None,
            "embedded_checksum": None,
        }
    if allowed_resolvers is not None and resolved_from not in allowed_resolvers:
        return {
            "verified": False,
            "error": f"resolver not allowed: {resolved_from}",
            "output_path": str(output_path),
            "resolved_from": resolved_from,
            "fetch_error": None,
            "expected_checksum": str(entry.get("checksum_sha256", "")).strip() or None,
            "actual_checksum": None,
            "embedded_checksum": None,
        }
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "verified": False,
            "error": f"invalid export payload json: {output_path}",
            "output_path": str(output_path),
            "resolved_from": resolved_from,
            "fetch_error": None,
            "expected_checksum": str(entry.get("checksum_sha256", "")).strip() or None,
            "actual_checksum": None,
            "embedded_checksum": None,
        }
    if not isinstance(payload, dict):
        return {
            "verified": False,
            "error": f"invalid export payload: {output_path}",
            "output_path": str(output_path),
            "resolved_from": resolved_from,
            "fetch_error": None,
            "expected_checksum": str(entry.get("checksum_sha256", "")).strip() or None,
            "actual_checksum": None,
            "embedded_checksum": None,
        }
    file_entries = payload.get("entries", [])
    if not isinstance(file_entries, list):
        file_entries = []
    actual_checksum = compute_entries_checksum(file_entries)
    expected_checksum = str(entry.get("checksum_sha256", "")).strip()
    embedded_checksum = str(payload.get("checksum_sha256", "")).strip()
    verified = (
        bool(expected_checksum)
        and actual_checksum == expected_checksum
        and (not embedded_checksum or embedded_checksum == actual_checksum)
    )
    error = None if verified else "verification failed: checksum mismatch"
    return {
        "verified": verified,
        "error": error,
        "output_path": str(output_path),
        "resolved_from": resolved_from,
        "fetch_error": None,
        "expected_checksum": expected_checksum or None,
        "actual_checksum": actual_checksum,
        "embedded_checksum": embedded_checksum or None,
    }


def build_verify_trend_summary(
    *,
    manifest_entries: list[dict[str, object]],
    window_size: int,
    archive_dir: Path | None,
    fetch_cmd: str,
    fetch_timeout: int,
    allowed_resolvers: set[str] | None,
) -> dict[str, object]:
    recent_entries = manifest_entries[-window_size:]
    passed_total = 0
    failed_total = 0
    fetch_failure_total = 0
    resolver_source_counts: dict[str, int] = {}
    failed_manifest_entry_ids: list[str] = []
    for entry in recent_entries:
        verify_result = verify_manifest_entry(
            entry,
            archive_dir=archive_dir,
            fetch_cmd=fetch_cmd,
            fetch_timeout=fetch_timeout,
            allowed_resolvers=allowed_resolvers,
        )
        resolved_from = str(verify_result.get("resolved_from") or "unknown")
        resolver_source_counts[resolved_from] = resolver_source_counts.get(resolved_from, 0) + 1
        if verify_result.get("fetch_error"):
            fetch_failure_total += 1
        if bool(verify_result.get("verified")):
            passed_total += 1
            continue
        failed_total += 1
        entry_id = str(entry.get("id", "")).strip() or "unknown"
        failed_manifest_entry_ids.append(entry_id)

    sample_size = len(recent_entries)
    pass_rate = round(passed_total / sample_size, 4) if sample_size else None
    return {
        "window_size": window_size,
        "sample_size": sample_size,
        "passed_total": passed_total,
        "failed_total": failed_total,
        "fetch_failure_total": fetch_failure_total,
        "resolver_source_counts": resolver_source_counts,
        "pass_rate": pass_rate,
        "failed_manifest_entry_ids": failed_manifest_entry_ids,
    }


if list_effective_policy_distributions:
    if distribute_effective_policy_dir is None:
        raise SystemExit(
            "invalid mode: --list-effective-policy-distributions requires --distribute-effective-policy-dir"
        )
    list_result = list_effective_policy_distribution_index(
        output_dir=distribute_effective_policy_dir,
        limit=list_effective_policy_distributions_limit,
        mode_filter=list_effective_policy_distributions_mode_raw or None,
        since_at=list_effective_policy_distributions_since,
    )
    selected_total = int(list_result.get("selected_total", 0))
    list_empty_guard_passed = selected_total > 0
    list_min_selected = list_effective_policy_min_selected
    list_min_selected_guard_passed = (
        True
        if list_min_selected is None
        else selected_total >= list_min_selected
    )
    list_result["list_integrity_fail_on_error"] = list_effective_policy_fail_on_integrity_error
    list_result["list_empty_fail_on_error"] = list_effective_policy_fail_on_empty
    list_result["list_empty_guard_passed"] = list_empty_guard_passed
    list_result["list_min_selected"] = list_min_selected
    list_result["list_min_selected_guard_passed"] = list_min_selected_guard_passed
    if not list_empty_guard_passed:
        recommendations = list_result.get("list_recommendations")
        if isinstance(recommendations, list):
            recommendations.append(
                "confirm distribution pipeline produced entries before enabling release gate"
            )
            list_result["list_recommendations"] = recommendations[:10]
    if (
        list_min_selected is not None
        and not list_min_selected_guard_passed
    ):
        recommendations = list_result.get("list_recommendations")
        if isinstance(recommendations, list):
            recommendations.append(
                f"lower --list-effective-policy-min-selected or increase entries to at least {list_min_selected}"
            )
            list_result["list_recommendations"] = recommendations[:10]
    if list_effective_policy_state_file is not None:
        list_state_payload = {
            "version": 1,
            "tool": "v3_metrics_rollback_approval_gc",
            "mode": "list_effective_policy_distributions",
            "updated_at": datetime.now().astimezone().isoformat(),
            "list": {
                "distribution_dir": list_result.get("distribution_dir"),
                "matched_total": list_result.get("matched_total"),
                "selected_total": list_result.get("selected_total"),
                "integrity_checked_total": list_result.get("integrity_checked_total"),
                "integrity_failed_total": list_result.get("integrity_failed_total"),
                "integrity_guard_passed": list_result.get("integrity_guard_passed"),
                "list_safety_risk_level": list_result.get("list_safety_risk_level"),
                "list_recommendations": list_result.get("list_recommendations"),
                "summary": list_result.get("summary"),
                "integrity_fail_on_error": list_effective_policy_fail_on_integrity_error,
                "empty_fail_on_error": list_effective_policy_fail_on_empty,
                "empty_guard_passed": list_empty_guard_passed,
                "min_selected": list_min_selected,
                "min_selected_guard_passed": list_min_selected_guard_passed,
                "mode_filter": list_result.get("mode_filter"),
                "since_iso": list_result.get("since_iso"),
                "limit": list_result.get("limit"),
            },
        }
        write_state_snapshot(list_effective_policy_state_file, list_state_payload)
        list_result["state_file"] = str(list_effective_policy_state_file)
    print(json.dumps(list_result, ensure_ascii=False))
    if (
        list_effective_policy_fail_on_integrity_error
        and not bool(list_result.get("integrity_guard_passed", False))
    ):
        raise SystemExit(1)
    if list_effective_policy_fail_on_empty and not list_empty_guard_passed:
        raise SystemExit(1)
    if (
        list_min_selected is not None
        and not list_min_selected_guard_passed
    ):
        raise SystemExit(1)
    raise SystemExit(0)


if restore_effective_policy_distributions:
    if distribute_effective_policy_dir is None:
        raise SystemExit(
            "invalid mode: --restore-effective-policy-distributions requires --distribute-effective-policy-dir"
        )
    restore_result = restore_effective_policy_distribution_index(
        output_dir=distribute_effective_policy_dir,
        limit=restore_effective_policy_distributions_limit,
        since_at=restore_effective_policy_distributions_since,
        dry_run=dry_run,
        verify_integrity=restore_effective_policy_verify_integrity,
        fail_on_integrity_error=restore_effective_policy_fail_on_integrity_error,
        remap_from=restore_effective_policy_remap_from,
        remap_to=restore_effective_policy_remap_to,
    )
    restore_min_restored = restore_effective_policy_min_restored
    restore_effective_count = int(
        restore_result.get("would_restore_total" if dry_run else "restored_total", 0)
    )
    restore_min_restored_guard_passed = (
        True
        if restore_min_restored is None
        else restore_effective_count >= restore_min_restored
    )
    restore_result["restore_min_restored"] = restore_min_restored
    restore_result["restore_min_restored_guard_passed"] = restore_min_restored_guard_passed
    restore_result["restore_min_restored_effective_count"] = restore_effective_count
    if (
        restore_min_restored is not None
        and not restore_min_restored_guard_passed
    ):
        recommendations = restore_result.get("restore_recommendations")
        if isinstance(recommendations, list):
            recommendations.append(
                f"lower --restore-effective-policy-min-restored or increase restorable entries to at least {restore_min_restored}"
            )
            restore_result["restore_recommendations"] = recommendations[:10]
    if restore_effective_policy_state_file is not None:
        restore_state_payload = {
            "version": 1,
            "tool": "v3_metrics_rollback_approval_gc",
            "mode": "restore_effective_policy_distributions",
            "updated_at": datetime.now().astimezone().isoformat(),
            "restore": {
                "summary": restore_result.get("summary"),
                "distribution_dir": restore_result.get("distribution_dir"),
                "restore_candidate_total": restore_result.get("restore_candidate_total"),
                "would_restore_total": restore_result.get("would_restore_total"),
                "restored_total": restore_result.get("restored_total"),
                "skipped_existing_total": restore_result.get("skipped_existing_total"),
                "integrity_guard_passed": restore_result.get("integrity_guard_passed"),
                "integrity_failed_total": restore_result.get("integrity_failed_total"),
                "restore_safety_risk_level": restore_result.get("restore_safety_risk_level"),
                "min_restored": restore_min_restored,
                "min_restored_guard_passed": restore_min_restored_guard_passed,
                "min_restored_effective_count": restore_effective_count,
            },
        }
        write_state_snapshot(restore_effective_policy_state_file, restore_state_payload)
        restore_result["state_file"] = str(restore_effective_policy_state_file)
    print(json.dumps(restore_result, ensure_ascii=False))
    if (
        restore_effective_policy_fail_on_integrity_error
        and not bool(restore_result.get("integrity_guard_passed", False))
    ):
        raise SystemExit(1)
    if (
        restore_min_restored is not None
        and not restore_min_restored_guard_passed
    ):
        raise SystemExit(1)
    raise SystemExit(0)


if signer_preflight:
    run_time = datetime.now().astimezone().isoformat()
    preflight_payload = {
        "mode": "signer_preflight",
        "generated_at": run_time,
        "probe": "wherecode-metrics-rollback-approval-gc",
    }
    signer_result = None
    try:
        signer_result = run_signer_hook(
            signer_cmd=manifest_signer_cmd,
            timeout_seconds=manifest_signer_timeout,
            payload=preflight_payload,
        )
    except SystemExit as exc:
        message = str(exc).strip() or "signer preflight failed"
        success = False
    else:
        message = "signer preflight passed"
        success = True
    result = {
        "signer_preflight": True,
        "success": success,
        "policy_profile": policy_profile,
        "effective_policy": effective_policy,
        "manifest_signer_cmd": manifest_signer_cmd,
        "manifest_signer_timeout": manifest_signer_timeout,
        "key_id": signer_result["key_id"] if signer_result is not None else None,
        "signature_preview": (
            f"{signer_result['signature'][:16]}..." if signer_result is not None else None
        ),
        "summary": message,
    }
    if preflight_history_path_raw:
        history_path = Path(preflight_history_path_raw)
        history_entry = {
            "created_at": run_time,
            "success": success,
            "summary": message,
            "manifest_signer_cmd": manifest_signer_cmd,
            "manifest_signer_timeout": manifest_signer_timeout,
            "key_id": result["key_id"],
        }
        history_entries = load_jsonl_entries(history_path)
        append_jsonl_entry(history_path, history_entry)
        history_entries.append(history_entry)
        result["history_path"] = str(history_path)
        result["history_trend"] = build_preflight_history_trend(
            history_entries=history_entries,
            window_size=preflight_history_window,
        )
    preflight_slo_violations: list[str] = []
    history_trend = result.get("history_trend")
    if (
        history_trend is not None
        and isinstance(history_trend, dict)
        and preflight_slo_min_pass_rate is not None
    ):
        history_pass_rate = history_trend.get("pass_rate")
        if (
            history_pass_rate is not None
            and float(history_pass_rate) < preflight_slo_min_pass_rate
        ):
            preflight_slo_violations.append(
                f"preflight pass_rate {history_pass_rate} < {preflight_slo_min_pass_rate}"
            )
    if (
        history_trend is not None
        and isinstance(history_trend, dict)
        and preflight_slo_max_consecutive_failures is not None
    ):
        consecutive_failures = int(history_trend.get("consecutive_failures", 0))
        if consecutive_failures > preflight_slo_max_consecutive_failures:
            preflight_slo_violations.append(
                f"preflight consecutive_failures {consecutive_failures} > {preflight_slo_max_consecutive_failures}"
            )
    policy_passed = len(preflight_slo_violations) == 0
    if preflight_slo_violations:
        result["slo_violations"] = preflight_slo_violations
        result["summary"] = f"{result['summary']}; policy gate failed"
    result["policy_passed"] = policy_passed
    if export_effective_policy_path is not None:
        export_effective_policy_snapshot(
            output_path=export_effective_policy_path,
            mode="signer_preflight",
            effective_policy_payload=effective_policy,
        )
        result["effective_policy_path"] = str(export_effective_policy_path)
    if distribute_effective_policy_dir is not None:
        distribution_result = distribute_effective_policy_snapshot(
            output_dir=distribute_effective_policy_dir,
            mode="signer_preflight",
            effective_policy_payload=effective_policy,
            cleanup_enabled=distribute_effective_policy_cleanup_enabled,
            retain_seconds=distribute_effective_policy_retain_seconds,
            keep_latest=distribute_effective_policy_keep_latest_value,
        )
        result["effective_policy_distribution_dir"] = str(distribute_effective_policy_dir)
        result["effective_policy_distribution_latest"] = distribution_result["latest_path"]
        result["effective_policy_distribution_versioned"] = distribution_result["versioned_path"]
        result["effective_policy_distribution_versioned_checksum_sha256"] = distribution_result["versioned_checksum_sha256"]
        result["effective_policy_distribution_index_path"] = distribution_result["index_path"]
        result["effective_policy_distribution_index_entry_id"] = distribution_result["index_entry_id"]
        result["effective_policy_distribution_index_compaction_max_entries"] = distribution_result["index_compaction_max_entries"]
        result["effective_policy_distribution_index_compaction_removed_total"] = distribution_result["index_compaction_removed_total"]
        result["effective_policy_distribution_index_total_after_compaction"] = distribution_result["index_total_after_compaction"]
        result["effective_policy_distribution_index_archive_path"] = distribution_result["index_archive_path"]
        result["effective_policy_distribution_index_archive_appended_total"] = distribution_result["index_archive_appended_total"]
        result["effective_policy_distribution_cleanup_enabled"] = distribution_result["cleanup_enabled"]
        result["effective_policy_distribution_retain_seconds"] = distribution_result["retain_seconds"]
        result["effective_policy_distribution_keep_latest"] = distribution_result["keep_latest"]
        result["effective_policy_distribution_removed_total"] = distribution_result["removed_total"]
        result["effective_policy_distribution_remaining_versioned_total"] = distribution_result["remaining_versioned_total"]
        result["effective_policy_distribution_removed_paths"] = distribution_result["removed_paths"]
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if success and policy_passed else 1)

store = MetricsAlertPolicyStore(
    policy_path,
    audit_path,
    approval_path,
    purge_audit_path,
    rollback_approval_ttl_seconds=ttl_seconds,
)
if export_purge_audits:
    created_after = parse_iso(export_from_iso)
    created_before = parse_iso(export_to_iso)
    entries = store.list_rollback_approval_purge_audits(
        limit=export_limit,
        event_type=export_event_type or None,
        created_after=created_after,
        created_before=created_before,
    )
    serializable_entries = []
    for entry in entries:
        payload = dict(entry)
        created_at = payload.get("created_at")
        if created_at is not None and hasattr(created_at, "isoformat"):
            payload["created_at"] = created_at.isoformat()
        serializable_entries.append(payload)
    generated_at = datetime.now().astimezone().isoformat()
    checksum_sha256 = compute_entries_checksum(serializable_entries)
    export_payload = {
        "exported_total": len(serializable_entries),
        "limit": export_limit,
        "event_type": export_event_type or None,
        "created_after": created_after.isoformat() if created_after is not None else None,
        "created_before": created_before.isoformat() if created_before is not None else None,
        "generated_at": generated_at,
        "checksum_scope": "entries",
        "checksum_sha256": checksum_sha256,
        "entries": serializable_entries,
    }
    if export_output_path:
        output_path = Path(export_output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(export_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = {
            "exported_total": len(serializable_entries),
            "output_path": str(output_path),
            "checksum_sha256": checksum_sha256,
        }
        if manifest_path_raw:
            manifest_path = Path(manifest_path_raw)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            if manifest_signer_cmd:
                signer_payload = {
                    "checksum_scope": "entries",
                    "checksum_sha256": checksum_sha256,
                    "output_path": str(output_path),
                    "generated_at": generated_at,
                    "event_type": export_event_type or None,
                    "created_after": export_payload["created_after"],
                    "created_before": export_payload["created_before"],
                    "exported_total": len(serializable_entries),
                }
                signer_result = run_signer_hook(
                    signer_cmd=manifest_signer_cmd,
                    timeout_seconds=manifest_signer_timeout,
                    payload=signer_payload,
                )
                signed_key_id = signer_result["key_id"]
                signed_signature = signer_result["signature"]
            else:
                signed_key_id = None
                signed_signature = None
            manifest_entry_id = f"exp_{int(datetime.now().timestamp() * 1000)}"
            manifest_entry = {
                "id": manifest_entry_id,
                "created_at": generated_at,
                "output_path": str(output_path),
                "exported_total": len(serializable_entries),
                "event_type": export_event_type or None,
                "created_after": export_payload["created_after"],
                "created_before": export_payload["created_before"],
                "checksum_scope": "entries",
                "checksum_sha256": checksum_sha256,
                "key_id": manifest_key_id or signed_key_id,
                "signature": manifest_signature or signed_signature,
            }
            with manifest_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
            result["manifest_path"] = str(manifest_path)
            result["manifest_entry_id"] = manifest_entry_id
            if manifest_signer_cmd:
                result["manifest_signer_used"] = True
                result["manifest_signer_cmd"] = manifest_signer_cmd
    else:
        result = export_payload
elif verify_manifest:
    manifest_path = Path(manifest_path_raw)
    entries = load_manifest_entries(manifest_path)
    if not entries:
        raise SystemExit("manifest has no entries")
    if verify_manifest_id:
        selected = None
        for item in entries:
            if str(item.get("id", "")).strip() == verify_manifest_id:
                selected = item
                break
        if selected is None:
            raise SystemExit(f"manifest entry not found: {verify_manifest_id}")
    else:
        selected = entries[-1]

    verify_result = verify_manifest_entry(
        selected,
        override_output_path=verify_export_file or None,
        archive_dir=verify_archive_dir,
        fetch_cmd=verify_fetch_cmd,
        fetch_timeout=verify_fetch_timeout,
        allowed_resolvers=allowed_resolvers,
    )
    output_path_raw = verify_result.get("output_path")
    if output_path_raw is None:
        raise SystemExit(str(verify_result.get("error") or "manifest entry has no output_path"))
    verified = bool(verify_result.get("verified"))
    expected_checksum = str(verify_result.get("expected_checksum") or "")
    actual_checksum = str(verify_result.get("actual_checksum") or "")
    embedded_checksum_value = verify_result.get("embedded_checksum")
    embedded_checksum = str(embedded_checksum_value) if embedded_checksum_value is not None else ""
    trend_summary = build_verify_trend_summary(
        manifest_entries=entries,
        window_size=verify_trend_window,
        archive_dir=verify_archive_dir,
        fetch_cmd=verify_fetch_cmd,
        fetch_timeout=verify_fetch_timeout,
        allowed_resolvers=allowed_resolvers,
    )
    verify_slo_violations: list[str] = []
    trend_pass_rate = trend_summary.get("pass_rate")
    if verify_slo_min_pass_rate is not None and trend_pass_rate is not None:
        if float(trend_pass_rate) < verify_slo_min_pass_rate:
            verify_slo_violations.append(
                f"verify trend pass_rate {trend_pass_rate} < {verify_slo_min_pass_rate}"
            )
    trend_fetch_failures = int(trend_summary.get("fetch_failure_total", 0))
    if (
        verify_slo_max_fetch_failures is not None
        and trend_fetch_failures > verify_slo_max_fetch_failures
    ):
        verify_slo_violations.append(
            f"verify trend fetch_failure_total {trend_fetch_failures} > {verify_slo_max_fetch_failures}"
        )
    policy_passed = len(verify_slo_violations) == 0
    if verified and policy_passed:
        summary = "verification passed"
    elif not verified:
        summary = str(verify_result.get("error") or "verification failed: checksum mismatch")
    else:
        summary = "verification failed: policy gate violation"
    result = {
        "verified": verified,
        "policy_passed": policy_passed,
        "policy_profile": policy_profile,
        "effective_policy": effective_policy,
        "manifest_path": str(manifest_path),
        "manifest_entry_id": str(selected.get("id", "")).strip() or None,
        "output_path": output_path_raw,
        "resolved_from": str(verify_result.get("resolved_from") or "manifest_output_path"),
        "verify_archive_dir": str(verify_archive_dir) if verify_archive_dir is not None else None,
        "verify_fetch_cmd": verify_fetch_cmd or None,
        "allowed_resolvers": sorted(allowed_resolvers) if allowed_resolvers is not None else None,
        "fetch_error": verify_result.get("fetch_error"),
        "expected_checksum": expected_checksum or None,
        "actual_checksum": actual_checksum or None,
        "embedded_checksum": embedded_checksum or None,
        "key_id": str(selected.get("key_id", "")).strip() or None,
        "signature_present": bool(str(selected.get("signature", "")).strip()),
        "trend_summary": trend_summary,
        "summary": summary,
    }
    if verify_slo_violations:
        result["slo_violations"] = verify_slo_violations
    if export_effective_policy_path is not None:
        export_effective_policy_snapshot(
            output_path=export_effective_policy_path,
            mode="verify_manifest",
            effective_policy_payload=effective_policy,
        )
        result["effective_policy_path"] = str(export_effective_policy_path)
    if distribute_effective_policy_dir is not None:
        distribution_result = distribute_effective_policy_snapshot(
            output_dir=distribute_effective_policy_dir,
            mode="verify_manifest",
            effective_policy_payload=effective_policy,
            cleanup_enabled=distribute_effective_policy_cleanup_enabled,
            retain_seconds=distribute_effective_policy_retain_seconds,
            keep_latest=distribute_effective_policy_keep_latest_value,
        )
        result["effective_policy_distribution_dir"] = str(distribute_effective_policy_dir)
        result["effective_policy_distribution_latest"] = distribution_result["latest_path"]
        result["effective_policy_distribution_versioned"] = distribution_result["versioned_path"]
        result["effective_policy_distribution_versioned_checksum_sha256"] = distribution_result["versioned_checksum_sha256"]
        result["effective_policy_distribution_index_path"] = distribution_result["index_path"]
        result["effective_policy_distribution_index_entry_id"] = distribution_result["index_entry_id"]
        result["effective_policy_distribution_index_compaction_max_entries"] = distribution_result["index_compaction_max_entries"]
        result["effective_policy_distribution_index_compaction_removed_total"] = distribution_result["index_compaction_removed_total"]
        result["effective_policy_distribution_index_total_after_compaction"] = distribution_result["index_total_after_compaction"]
        result["effective_policy_distribution_index_archive_path"] = distribution_result["index_archive_path"]
        result["effective_policy_distribution_index_archive_appended_total"] = distribution_result["index_archive_appended_total"]
        result["effective_policy_distribution_cleanup_enabled"] = distribution_result["cleanup_enabled"]
        result["effective_policy_distribution_retain_seconds"] = distribution_result["retain_seconds"]
        result["effective_policy_distribution_keep_latest"] = distribution_result["keep_latest"]
        result["effective_policy_distribution_removed_total"] = distribution_result["removed_total"]
        result["effective_policy_distribution_remaining_versioned_total"] = distribution_result["remaining_versioned_total"]
        result["effective_policy_distribution_removed_paths"] = distribution_result["removed_paths"]
    if verify_report_output:
        report_path = Path(verify_report_output)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if verify_report_format == "json":
            report_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            report_lines = [
                "WhereCode Purge Audit Verification Report",
                f"Manifest Path: {manifest_path}",
                f"Manifest Entry: {result['manifest_entry_id']}",
                f"Export File: {output_path_raw}",
                f"Resolved From: {result['resolved_from']}",
                f"Fetch Error: {result['fetch_error'] or 'N/A'}",
                f"Policy Profile: {result['policy_profile']}",
                f"Policy Source: {result['effective_policy'].get('policy_source')}",
                f"Allowed Resolvers: {','.join(result['effective_policy'].get('allowed_resolvers') or []) or 'any'}",
                f"Policy Passed: {'yes' if result['policy_passed'] else 'no'}",
                f"Effective Policy Path: {result.get('effective_policy_path') or 'N/A'}",
                f"Key ID: {result['key_id'] or 'N/A'}",
                f"Signature Present: {'yes' if result['signature_present'] else 'no'}",
                f"Verified: {'yes' if verified else 'no'}",
                f"Expected Checksum: {expected_checksum or 'N/A'}",
                f"Actual Checksum: {actual_checksum or 'N/A'}",
                f"Embedded Checksum: {embedded_checksum or 'N/A'}",
                f"Trend Window: {trend_summary['window_size']}",
                f"Trend Sample: {trend_summary['sample_size']}",
                f"Trend Passed: {trend_summary['passed_total']}",
                f"Trend Failed: {trend_summary['failed_total']}",
                f"Trend Fetch Failures: {trend_summary['fetch_failure_total']}",
                f"Trend Pass Rate: {trend_summary['pass_rate'] if trend_summary['pass_rate'] is not None else 'N/A'}",
                f"Trend Failed Entries: {','.join(trend_summary['failed_manifest_entry_ids']) or 'none'}",
                f"SLO Violations: {','.join(result.get('slo_violations', [])) or 'none'}",
                f"Summary: {result['summary']}",
            ]
            report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        result["report_path"] = str(report_path)
        result["report_format"] = verify_report_format
    print(json.dumps(result, ensure_ascii=False))
    if not verified or not policy_passed:
        raise SystemExit(1)
    raise SystemExit(0)
elif rotate_exports:
    export_dir = Path(rotate_export_dir)
    files = sorted(
        [item for item in export_dir.glob("*.json") if item.is_file()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    now = datetime.now().astimezone()
    removed_paths = []
    kept_paths = []
    for index, file_path in enumerate(files):
        if index < rotate_keep_latest:
            kept_paths.append(str(file_path))
            continue
        if rotate_older_than_seconds is not None:
            age_seconds = now.timestamp() - file_path.stat().st_mtime
            if age_seconds < rotate_older_than_seconds:
                kept_paths.append(str(file_path))
                continue
        if not dry_run:
            file_path.unlink(missing_ok=True)
        removed_paths.append(str(file_path))
    result = {
        "dry_run": dry_run,
        "scanned_total": len(files),
        "removed_total": len(removed_paths),
        "remaining_total": len(files) - len(removed_paths),
        "keep_export_latest": rotate_keep_latest,
        "retain_seconds": rotate_older_than_seconds,
        "removed_paths": removed_paths,
        "kept_paths": kept_paths[:50],
    }
elif purge_audits:
    result = store.purge_rollback_approval_purge_audits(
        dry_run=dry_run,
        older_than_seconds=older_than_seconds,
        keep_latest=keep_latest,
        requested_by=requested_by or None,
    )
else:
    result = store.purge_rollback_approvals(
        remove_used=remove_used,
        remove_expired=remove_expired,
        dry_run=dry_run,
        older_than_seconds=older_than_seconds,
        requested_by=requested_by or None,
    )
print(json.dumps(result, ensure_ascii=False))
PY
