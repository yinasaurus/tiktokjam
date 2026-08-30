#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-8765}"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

PYTHON="$ROOT/.venv/bin/python"
if [ "${INSTALL:-0}" = "1" ]; then
  "$PYTHON" -m pip install -r requirements.txt
fi

"$PYTHON" -m pytest tests -q
echo "Starting demo UI at http://127.0.0.1:$PORT/"
"$PYTHON" -m ui --port "$PORT"
