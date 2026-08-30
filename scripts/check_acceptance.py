"""Internal acceptance gate over simulated customer sessions.

Default gate: TechnicalScore >= 0.80. Uses the official evaluator functions and
does not modify evaluator/ or data files.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starter.agent import Agent
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Run internal score acceptance gate")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--dataset", type=Path, default=Path("data/public_set.jsonl"))
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--scenario",
        choices=["buying", "browsing", "intent_override", "boundary"],
        default=None,
    )
    args = parser.parse_args()

    if not args.catalog.exists():
        raise SystemExit(f"missing catalog: {args.catalog}")
    if not args.dataset.exists():
        raise SystemExit(f"missing dataset: {args.dataset}")

    samples = load_jsonl(args.dataset)
    if args.scenario:
        samples = [s for s in samples if s.get("scenario_type") == args.scenario]
    rng = random.Random(args.seed)
    rng.shuffle(samples)
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]

    catalog_ids, categories, products = catalog_index(args.catalog)
    result = evaluate(Agent(args.catalog), samples, catalog_ids, categories, products)
    score = float(result["recommended_technical_score"])
    summary = {
        "threshold": args.threshold,
        "passed": score >= args.threshold,
        "sample_count": len(samples),
        "seed": args.seed,
        "scenario": args.scenario,
        "hit_rate_at_10": result["hit_rate_at_10"],
        "mrr": result["mrr"],
        "mttc": result["mttc"],
        "efficiency": result["efficiency"],
        "recommended_technical_score": result["recommended_technical_score"],
        "scenario_metrics": result.get("scenario_metrics", {}),
    }
    print(json.dumps(summary, indent=2))
    if score < args.threshold:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
