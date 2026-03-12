#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${DIR}"

python3 -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-18080}" --reload
