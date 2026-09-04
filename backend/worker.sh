#!/usr/bin/env bash
# Start a queue worker. Run as many as you need; they coordinate through the
# database, so two workers never claim the same job.
set -euo pipefail
cd "$(dirname "$0")"

# The venv layout differs by platform: bin/ on Linux and macOS, Scripts/ on
# Windows. Resolving it here is what lets one script serve both, including the
# Playwright webServer that boots the API for the E2E suite.
PY_BIN=./.venv/bin/python
[ -x "$PY_BIN" ] || PY_BIN=./.venv/Scripts/python.exe

exec "$PY_BIN" -m app.jobs.worker "$@"
