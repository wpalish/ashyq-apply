#!/usr/bin/env bash
# The API and worker for the demo and auth browser suites (E2E-DB-1), started
# by playwright.config.ts and playwright.auth.config.ts.
#
# Both suites used to start `backend/run.sh --with-worker` with no database URL,
# so a local run read the checkout's own backend/data database, grown by every
# earlier run and by seed_demo.py. CI's checkout is empty and never saw that;
# a developer's run failed at the journey's first assertion (HANDOFF §9,
# 2026-09-06: 5 failed / 64 did not run on a clean main). Now each suite gets
# a scratch directory, wiped on every start, holding the SQLite database, the
# HTTP cache and the export dir — exactly what CI starts from.
#
# Nothing is seeded: the journey starts its own demo run and the auth suite's
# persistence lives within one run. The mode (demo, knowledge, auth) is the
# config's `env`, stated there; this script sets only the paths. No network
# guard, unlike kb-env: these suites read fixtures.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$HERE/../../../backend" && pwd)"
SCRATCH="${E2E_SCRATCH_DIR:?E2E_SCRATCH_DIR names the scratch directory}"

# The directory is wiped below, so only a scratch directory of these suites is
# accepted: named e2e-demo* or e2e-auth*, directly under backend/data. Anything
# else — backend/data itself, a home directory, a kept folder — is refused
# before anything is removed (the kb harness's rule, security review 2026-10-22).
refuse() {
  echo "serve-api.sh: E2E_SCRATCH_DIR must be backend/data/e2e-demo* or backend/data/e2e-auth*; refusing to wipe $SCRATCH" >&2
  exit 64
}
case "$(basename -- "$SCRATCH")" in
  e2e-demo* | e2e-auth*) ;;
  *) refuse ;;
esac
# A fresh CI checkout has no backend/data yet.
mkdir -p "$BACKEND/data"
PARENT="$(cd "$(dirname -- "$SCRATCH")" 2>/dev/null && pwd -P)" || refuse
[ "$PARENT" = "$(cd "$BACKEND/data" 2>/dev/null && pwd -P)" ] || refuse

rm -rf -- "$SCRATCH"
mkdir -p "$SCRATCH"

export UNIMATCH_DATABASE_URL="sqlite:///$SCRATCH/unimatch.db"
export UNIMATCH_CACHE_DIR="$SCRATCH/httpcache"
export UNIMATCH_EXPORT_DIR="$SCRATCH/exports"

# run.sh migrates (`alembic upgrade head`) before it starts the worker and API.
exec bash "$BACKEND/run.sh" --with-worker
