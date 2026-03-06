#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SECRET_REGEX='AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{35}|sk-(live|proj)-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{40,}|-----BEGIN (RSA|EC|OPENSSH|DSA|PRIVATE) KEY-----'
ALLOWLIST_REGEX='sk-xxxxx|sk-test|sk-openai|change-me|your[-_]?key|dummy[-_]?key|example[-_]?key'

MODE="working-tree"
RANGE=""

usage() {
  cat <<'EOF'
Usage:
  bash scripts/check_secrets.sh [--working-tree|--staged|--all-history|--range <rev-range>]

Modes:
  --working-tree   scan tracked files in current checkout (default)
  --staged         scan staged file snapshots in index
  --all-history    scan every commit tree in repository history
  --range <range>  scan commits inside given git rev-list range
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --working-tree)
      MODE="working-tree"
      shift
      ;;
    --staged)
      MODE="staged"
      shift
      ;;
    --all-history)
      MODE="all-history"
      shift
      ;;
    --range)
      MODE="range"
      RANGE="${2:-}"
      if [[ -z "${RANGE}" ]]; then
        echo "missing value for --range"
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1"
      usage
      exit 2
      ;;
  esac
done

print_filtered_findings() {
  local data="$1"
  if [[ -z "${data}" ]]; then
    return 0
  fi
  printf '%s\n' "${data}" | grep -Ev "${ALLOWLIST_REGEX}" || true
}

scan_working_tree() {
  local findings file
  local -a tracked_files=()
  while IFS= read -r -d '' file; do
    tracked_files+=("${file}")
  done < <(git ls-files -z)
  if [[ ${#tracked_files[@]} -eq 0 ]]; then
    return 0
  fi
  findings="$(
    rg -n -S --hidden --no-ignore-vcs -e "${SECRET_REGEX}" -- "${tracked_files[@]}" 2>/dev/null || true
  )"
  print_filtered_findings "${findings}"
}

scan_staged() {
  local file findings line_matches match_line
  findings=""
  while IFS= read -r file; do
    [[ -z "${file}" ]] && continue
    if ! git cat-file -e ":${file}" 2>/dev/null; then
      continue
    fi
    line_matches="$(
      git show ":${file}" | rg -n -S -e "${SECRET_REGEX}" || true
    )"
    if [[ -z "${line_matches}" ]]; then
      continue
    fi
    while IFS= read -r match_line; do
      [[ -z "${match_line}" ]] && continue
      findings+="staged:${file}:${match_line}"$'\n'
    done <<< "${line_matches}"
  done < <(git diff --cached --name-only --diff-filter=ACMR)
  print_filtered_findings "${findings}"
}

scan_commit_tree() {
  local rev="$1"
  local findings
  findings="$(git grep -nE "${SECRET_REGEX}" "${rev}" -- . 2>/dev/null || true)"
  print_filtered_findings "${findings}"
}

scan_range() {
  local range="$1"
  local rev findings revs
  if ! revs="$(git rev-list "${range}" 2>/dev/null)"; then
    echo "invalid revision range: ${range}" >&2
    exit 2
  fi
  findings=""
  while IFS= read -r rev; do
    [[ -z "${rev}" ]] && continue
    findings+="$(scan_commit_tree "${rev}")"$'\n'
  done <<< "${revs}"
  print_filtered_findings "${findings}"
}

run_scan() {
  case "${MODE}" in
    working-tree)
      scan_working_tree
      ;;
    staged)
      scan_staged
      ;;
    all-history)
      scan_range "--all"
      ;;
    range)
      scan_range "${RANGE}"
      ;;
    *)
      echo "unsupported mode: ${MODE}"
      exit 2
      ;;
  esac
}

output="$(run_scan || true)"
if [[ -n "${output}" ]]; then
  echo "secret scan failed:"
  printf '%s\n' "${output}" | sed '/^$/d'
  exit 1
fi

echo "secret scan passed (${MODE})"
