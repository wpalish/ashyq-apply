#!/usr/bin/env bash
# Start a queue worker. Run as many as you need; they coordinate through the
# database, so two workers never claim the same job.
set -euo pipefail
cd "$(dirname "$0")"
exec ./.venv/bin/python -m app.jobs.worker "$@"
