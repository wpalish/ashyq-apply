#!/bin/bash
# Cloud session start: the backend venv, the frontend packages, and a clean /tmp.
# Idempotent; only installs what is missing. Runs synchronously so tests work from the first turn.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR"

if [ ! -x backend/.venv/bin/python ]; then
  # Python 3.12 exactly: 3.11 cannot parse the `type` aliases in app/.
  python3.12 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements-dev.txt
fi
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install --no-audit --no-fund --silent)
fi

# Crashed suites leave pgserver clusters (~1 GB each) in /tmp; a full disk breaks every worker.
scripts/clean_test_tmp.sh >&2 || true
free_kb=$(df -Pk "${TMPDIR:-/tmp}" | awk 'NR==2{print $4}')
if [ "$free_kb" -lt $((3 * 1024 * 1024)) ]; then
  echo "WARNING: only $((free_kb / 1024)) MB free; scripts/run_suite.sh will refuse to start under 3 GB." >&2
fi
