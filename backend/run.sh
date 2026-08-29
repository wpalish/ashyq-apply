#!/usr/bin/env bash
# Start the ASHYQ Apply API, and optionally a worker supervised alongside it.
#
# The API does not run jobs: a separate worker process consumes the durable
# queue (see docs/adr/0001-durable-job-queue.md). `--with-worker` starts one
# alongside for local development and for the E2E suite, where a single
# supervised process tree is simpler. docker-compose runs them as separate
# services, which is the production shape.
#
# This script is a supervisor, not a launcher. It used to set an EXIT trap to
# kill the worker and then `exec` uvicorn — but `exec` replaces the shell, so
# the shell that owned the trap no longer existed and the trap could never run.
# Every shutdown orphaned its worker to PPID 1.
#
# That was not theoretical. A worker orphaned at 11:56 was still running six and
# a half hours later, consuming jobs from the shared development database with
# the model definitions it had loaded at startup. It took three `documents` jobs
# produced by a newer API, failed each three times on a field it had never heard
# of, and buried them in the dead-letter state. Research stopped and nothing
# said why.
#
# So: no exec, both children owned, signals forwarded, every child waited for.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8099}"
WITH_WORKER=0
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --with-worker) WITH_WORKER=1 ;;
    *) ARGS+=("$arg") ;;
  esac
done

# Migrate exactly once, here, before anything starts. The API and the worker
# both refuse to serve against a database they do not match, and two processes
# migrating concurrently deadlocks SQLite and races on PostgreSQL.
./.venv/bin/python -m alembic upgrade head >/dev/null
export UNIMATCH_AUTO_MIGRATE=false

API_PID=""
WORKER_PID=""
SHUTTING_DOWN=0

# Terminate one child by its exact PID and wait for it. Never a pattern, never
# a process group: this script must not be able to kill a process it did not
# start, however the terminal it runs in is arranged.
stop_child() {
  local pid="$1" name="$2" waited=0
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || { wait "$pid" 2>/dev/null || true; return 0; }

  kill -TERM "$pid" 2>/dev/null || true
  # Ten seconds to leave politely. A worker mid-job finishes its lease
  # bookkeeping in that window; the job is durable either way.
  while [ "$waited" -lt 100 ]; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
    waited=$((waited + 1))
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "run.sh: $name (pid $pid) ignored SIGTERM, sending SIGKILL" >&2
    kill -KILL "$pid" 2>/dev/null || true
  fi
  # Reap it. Without this the process stays a zombie for as long as this
  # script lives, and `ps` still lists it — which is indistinguishable from a
  # leak to anything checking.
  wait "$pid" 2>/dev/null || true
}

shutdown() {
  local code="${1:-0}"
  # Re-entrancy matters: a second Ctrl-C while we are already stopping children
  # would otherwise restart this function and double-signal them.
  if [ "$SHUTTING_DOWN" = "1" ]; then return; fi
  SHUTTING_DOWN=1
  trap - EXIT INT TERM
  stop_child "$WORKER_PID" "worker"
  stop_child "$API_PID" "api"
  exit "$code"
}

# 130 and 143 are the conventional codes for a process ended by SIGINT and
# SIGTERM. A supervisor asked to stop has not crashed, and should not report a
# crash to whatever started it.
trap 'shutdown 130' INT
trap 'shutdown 143' TERM
trap 'shutdown $?' EXIT

if [ "$WITH_WORKER" = "1" ]; then
  ./.venv/bin/python -m app.jobs.worker &
  WORKER_PID=$!
  echo "worker started (pid $WORKER_PID)"
fi

./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" ${ARGS+"${ARGS[@]}"} &
API_PID=$!
echo "api started (pid $API_PID) on port $PORT"

# Wait for whichever child exits first, then take the other down with it.
#
# Polled rather than `wait -n`, which needs bash 4.3; macOS ships bash 3.2 and
# this script has to work on a developer's machine as well as in CI.
while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    set +e; wait "$API_PID"; api_code=$?; set -e
    # The API failing to bind is exactly when cleanup matters most, because
    # nobody is watching.
    shutdown "$api_code"
  fi
  if [ -n "$WORKER_PID" ] && ! kill -0 "$WORKER_PID" 2>/dev/null; then
    set +e; wait "$WORKER_PID"; worker_code=$?; set -e
    echo "run.sh: worker exited with $worker_code; stopping the API too" >&2
    # A dead worker means jobs silently stop being consumed. Serving an API
    # that accepts work nothing will ever pick up is worse than being down.
    shutdown "$worker_code"
  fi
  sleep 0.2
done
