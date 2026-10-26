#!/usr/bin/env bash
# The one way to run the backend suite when several sessions share a machine.
#   scripts/run_suite.sh                 # the full suite, -n 4
#   scripts/run_suite.sh tests/test_x.py # any pytest arguments
# - At most two suites run at once (two flock slots); a third waits for a slot.
# - Refuses to start with under 3 GB free: a full suite with pgserver needs ~1 GB per worker.
# - On exit, however it ends, removes the pgserver clusters and temp files this run left behind.
set -uo pipefail
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
TMP=${TMPDIR:-/tmp}
MIN_FREE_KB=$((3 * 1024 * 1024))

free_kb=$(df -Pk "$TMP" | awk 'NR==2{print $4}')
if [ "$free_kb" -lt "$MIN_FREE_KB" ]; then
  "$ROOT/scripts/clean_test_tmp.sh"
  free_kb=$(df -Pk "$TMP" | awk 'NR==2{print $4}')
  if [ "$free_kb" -lt "$MIN_FREE_KB" ]; then
    echo "run_suite: only $((free_kb / 1024)) MB free in $TMP (need 3 GB); not starting." >&2
    exit 3
  fi
fi

exec 8>"$TMP/unimatch-suite.slot1" 9>"$TMP/unimatch-suite.slot2"
if ! flock -n 8 && ! flock -n 9; then
  echo "run_suite: two suites already running; waiting for a slot..." >&2
  flock 8
fi

# A private temp dir per run: pgserver clusters and pytest's basetemp land in it, so cleanup
# removes this run's leftovers and never a concurrent suite's.
RUN_TMP=$(mktemp -d "$TMP/unimatch-suite-XXXXXX")
export TMPDIR=$RUN_TMP
cleanup() {
  pkill -f -- "-D $RUN_TMP/" 2>/dev/null
  sleep 1
  rm -rf -- "$RUN_TMP"
}
trap cleanup EXIT INT TERM

cd "$ROOT/backend"
[ $# -eq 0 ] && set -- -n 4 tests
.venv/bin/pytest -q -p no:cacheprovider -o addopts="" "$@"
