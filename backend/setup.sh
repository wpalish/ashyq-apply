#!/usr/bin/env bash
# One-shot setup: Python 3.12 venv, dependencies, demo corpus, browser.
set -euo pipefail
cd "$(dirname "$0")"

if command -v uv >/dev/null 2>&1; then
  UV=uv
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
else
  echo "uv not found. Install it: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  echo "Or create a Python 3.12 venv yourself and pip install -r requirements-dev.txt" >&2
  exit 1
fi

echo "==> Python 3.12 virtual environment"
"$UV" python install 3.12
"$UV" venv --python 3.12 .venv

echo "==> Dependencies"
# uv writes bin/ on Linux and macOS, Scripts/ on Windows.
PY_BIN=.venv/bin/python
[ -x "$PY_BIN" ] || PY_BIN=.venv/Scripts/python.exe
"$UV" pip install --python "$PY_BIN" -r requirements-dev.txt

echo "==> Demo corpus"
"$PY_BIN" -m app.corpus.build

echo "==> Chromium for the browser tier and for E2E"
"$PY_BIN" -m playwright install chromium

echo
echo "Setup complete. Start the API with:  ./run.sh"
