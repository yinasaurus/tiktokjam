"""Measure evaluator score and respond() latency for a rerank configuration."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import Agent
from agent.config import Config
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl


class TimedAgent:
    def __init__(self, inner: Agent) -> None:
        self.inner = inner
        self.latencies_ms: list[float] = []

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.inner.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        t0 = time.perf_counter()
        try:
            return self.inner.respond(session_id, user_message, turn, top_k)
        finally:
            self.latencies_ms.append((time.perf_counter() - t0) * 1000.0)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((pct / 100.0) * (len(ordered) - 1))))
    return round(ordered[idx], 3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark reranker latency")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--dataset", type=Path, default=Path("data/public_set.jsonl"))
    parser.add_argument("--mode", choices=["off", "heuristic", "ltr", "cascade"], default="heuristic")
    parser.add_argument(
        "--ltr-model",
        type=Path,
        default=None,
        help="Optional LightGBM model path for research runs; default remains models/ltr.txt.",
    )
    parser.add_argument("--output", type=Path, default=Path("eval_output/reranker_bench.json"))
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected sessions")
    parser.add_argument(
        "--scenario",
        choices=["buying", "browsing", "intent_override", "boundary"],
        default=None,
        help="Run only one scenario type",
    )
    args = parser.parse_args()

    if not args.catalog.exists():
        raise SystemExit(f"missing catalog: {args.catalog}")
    if not args.dataset.exists():
        raise SystemExit(f"missing dataset: {args.dataset}")

    print(f"loading dataset: {args.dataset}", flush=True)
    samples = load_jsonl(args.dataset)
    if args.scenario:
        samples = [sample for sample in samples if sample.get("scenario_type") == args.scenario]
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]
    print(f"selected sessions: {len(samples)}", flush=True)
    print(f"loading catalog index: {args.catalog}", flush=True)
    catalog_ids, categories, products = catalog_index(args.catalog)
    print(f"benchmarking mode={args.mode}", flush=True)
    config = replace(Config(), rerank_mode=args.mode)
    if args.ltr_model is not None:
        config = replace(config, ltr_model_path=str(args.ltr_model))
    agent = TimedAgent(Agent(args.catalog, config=config))
    result = evaluate(agent, samples, catalog_ids, categories, products)
    latencies = agent.latencies_ms
    summary = {
        "mode": args.mode,
        "ltr_model": None if args.ltr_model is None else str(args.ltr_model),
        "turns": len(latencies),
        "latency_ms": {
            "mean": None if not latencies else round(statistics.fmean(latencies), 3),
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "max": None if not latencies else round(max(latencies), 3),
        },
        "score": {
            "hit_rate_at_10": result["hit_rate_at_10"],
            "mrr": result["mrr"],
            "mttc": result["mttc"],
            "efficiency": result["efficiency"],
            "recommended_technical_score": result["recommended_technical_score"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
