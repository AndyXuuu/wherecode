#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_files=(
  "${DIR}/evolve.json"
  "${DIR}/scripts/run.sh"
  "${DIR}/scripts/seed.sh"
  "${DIR}/scripts/autoevolve.sh"
  "${DIR}/scripts/today_sentiment.sh"
  "${DIR}/backend/app/main.py"
  "${DIR}/backend/app/analyzer.py"
  "${DIR}/backend/app/models.py"
  "${DIR}/backend/tests/test_analyzer.py"
  "${DIR}/frontend/index.html"
)

for path in "${required_files[@]}"; do
  test -f "${path}"
done

python3 -m json.tool "${DIR}/evolve.json" >/dev/null
python3 -m py_compile "${DIR}/backend/app/models.py" "${DIR}/backend/app/analyzer.py" "${DIR}/backend/app/main.py"
PYTHONPATH="${DIR}/backend" python3 -m unittest discover -s "${DIR}/backend/tests" -p 'test_*.py' >/dev/null

echo "subproject checks passed: ${DIR}"
