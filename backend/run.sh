#!/usr/bin/env bash
# Start the UniMatch API on the port the frontend dev server proxies to.
set -euo pipefail
cd "$(dirname "$0")"
exec ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8099}" "$@"
