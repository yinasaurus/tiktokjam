#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
WITH_DATA=0
WITH_LTR=0
for arg in "$@"; do
  case "$arg" in
    --with-data|-WithData) WITH_DATA=1 ;;
    --with-ltr|-WithLtr) WITH_LTR=1 ;;
  esac
done

PYTHON="python3"
[ -x ".venv/bin/python" ] && PYTHON="$ROOT/.venv/bin/python"

"$PYTHON" -m pytest tests -q
"$PYTHON" -m compileall agent scripts tools evaluator ui -q
"$PYTHON" scripts/smoke_session.py
"$PYTHON" scripts/synthetic_customer_gate.py --threshold 0.80 --trials 100

if [ "$WITH_DATA" -eq 1 ]; then
  [ -f data/catalog.jsonl ] || { echo "Missing data/catalog.jsonl" >&2; exit 1; }
  [ -f data/public_set.jsonl ] || { echo "Missing data/public_set.jsonl" >&2; exit 1; }
  "$PYTHON" -m evaluator.local_evaluator --catalog data/catalog.jsonl --dataset data/public_set.jsonl --output results.json
  "$PYTHON" scripts/run_ablations.py
  "$PYTHON" scripts/bench_reranker.py --mode heuristic
  if [ "$WITH_LTR" -eq 1 ]; then
    [ -f models/ltr.txt ] || { echo "Missing models/ltr.txt" >&2; exit 1; }
    "$PYTHON" scripts/bench_reranker.py --mode ltr
  fi
fi

git status --short
