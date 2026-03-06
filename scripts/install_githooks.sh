#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -d ".git" ]]; then
  echo "not a git repository: ${ROOT_DIR}"
  exit 1
fi

chmod +x scripts/check_secrets.sh
chmod +x .githooks/pre-commit
chmod +x .githooks/pre-push

git config core.hooksPath .githooks

echo "git hooks installed"
echo "core.hooksPath=$(git config --get core.hooksPath)"
