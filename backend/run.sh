#!/usr/bin/env bash
# Start the ASHYQ Apply API.
#
# The API does not run jobs: a separate worker process consumes the durable
# queue (see docs/adr/0001-durable-job-queue.md). `--with-worker` starts one
# alongside for local development and for the E2E suite, where a single
# supervised process tree is simpler. docker-compose runs them as separate
# services, which is the production shape.
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

if [ "$WITH_WORKER" = "1" ]; then
  ./.venv/bin/python -m app.jobs.worker &
  WORKER_PID=$!
  # Take the worker down with the API rather than orphaning it.
  trap 'kill "$WORKER_PID" 2>/dev/null || true' EXIT INT TERM
  echo "worker started (pid $WORKER_PID)"
fi

exec ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" ${ARGS+"${ARGS[@]}"}
