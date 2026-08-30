#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
CATALOG="${CATALOG:-data/catalog.jsonl}"
DATASET="${DATASET:-data/public_set.jsonl}"
OUTPUT="${OUTPUT:-results.json}"
PYTHON="python3"
[ -x ".venv/bin/python" ] && PYTHON="$ROOT/.venv/bin/python"

[ -f "$CATALOG" ] || { echo "Missing catalog at $CATALOG" >&2; exit 1; }
[ -f "$DATASET" ] || { echo "Missing public set at $DATASET" >&2; exit 1; }

"$PYTHON" -m evaluator.local_evaluator --catalog "$CATALOG" --dataset "$DATASET" --output "$OUTPUT"
echo "Wrote $OUTPUT (gitignored)"
