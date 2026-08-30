"""Print a compact ranking of ablation summary files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ablation summary JSON files")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    rows: list[tuple[float, str, str, float, float]] = []
    for path in args.paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for variant, metrics in data.items():
            score = float(metrics.get("recommended_technical_score") or 0.0)
            hit = float(metrics.get("hit_rate_at_10") or 0.0)
            mrr = float(metrics.get("mrr") or 0.0)
            rows.append((score, path.name, variant, hit, mrr))

    print(f"{'score':>9} {'hit@10':>9} {'mrr':>9} {'file':30} variant")
    print("-" * 80)
    for score, filename, variant, hit, mrr in sorted(rows, reverse=True):
        print(f"{score:9.6f} {hit:9.6f} {mrr:9.6f} {filename:30} {variant}")


if __name__ == "__main__":
    main()
