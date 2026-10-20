#!/usr/bin/env bash
# The API and worker for the kb-mode browser journey (E2E-KB), started by
# playwright.kb.config.ts. The setup of the manual smokes in
# docs/process/KB_E2E_SMOKE_2026-10-19.md, scripted:
#
# - kb mode, as an applicant gets it by default: demo off, the verified
#   knowledge base, no search provider, no browser tier;
# - a scratch SQLite database, cache and export dir, wiped on every start and
#   migrated by `alembic upgrade head` (backend/run.sh), never backend/data's
#   own database;
# - the network guard (sitecustomize.py beside this file) in every Python
#   process, plus a dead HTTP(S) proxy as a second fence. A probe proves the
#   guard blocks before anything starts; without that proof nothing starts.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$HERE/../../../backend" && pwd)"
SCRATCH="${E2E_KB_DIR:?E2E_KB_DIR names the scratch directory}"

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

export PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"
export NETGUARD_LOG="$SCRATCH/netguard.log"
export UNIMATCH_DEMO_MODE=false
export UNIMATCH_KNOWLEDGE_MODE=kb
export UNIMATCH_SEARCH_PROVIDER=none
export UNIMATCH_ENABLE_BROWSER_TIER=false
export UNIMATCH_DATABASE_URL="sqlite:///$SCRATCH/kb-journey.db"
export UNIMATCH_CACHE_DIR="$SCRATCH/cache"
export UNIMATCH_EXPORT_DIR="$SCRATCH/exports"
export HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9
export http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9
export NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1

PY_BIN="$BACKEND/.venv/bin/python"
[ -x "$PY_BIN" ] || PY_BIN="$BACKEND/.venv/Scripts/python.exe"

# The probe: a lookup of a name that is not local must be refused by the guard.
"$PY_BIN" - <<'PROBE'
import socket
import sys

try:
    socket.getaddrinfo("netguard-probe.invalid", 443)
except OSError as error:
    if "netguard" not in str(error):
        sys.exit(f"netguard probe: refused, but not by the guard: {error}")
else:
    sys.exit("netguard probe: a non-local lookup was not blocked")
PROBE
echo "PROBE blocked" >>"$NETGUARD_LOG"

exec bash "$BACKEND/run.sh" --with-worker
