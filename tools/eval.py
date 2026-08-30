"""Run official evaluator functions and print a regression table.

This wrapper does not modify evaluator/. It saves results.json plus timestamped
copies under runs/ so method changes can be compared locally.
"""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl

METRICS = ("hit_rate_at_10", "mrr", "mttc", "recommended_technical_score")


def load_agent_class(import_path: str):
    module_name, _, attr = import_path.partition(":")
    if not module_name or not attr:
        raise ValueError("agent import must look like module:ClassName")
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def metric_block(name: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "hit_rate_at_10": data.get("hit_rate_at_10", 0.0),
        "mrr": data.get("mrr", 0.0),
        "mttc": data.get("mttc"),
        "recommended_technical_score": data.get("recommended_technical_score")
        or technical_score(data),
    }


def technical_score(data: dict[str, Any]) -> float:
    mttc = float(data.get("mttc") or 11.0)
    efficiency = max(0.0, min(1.0, (11.0 - mttc) / 10.0))
    return round(
        0.50 * float(data.get("hit_rate_at_10") or 0.0)
        + 0.30 * float(data.get("mrr") or 0.0)
        + 0.20 * efficiency,
        6,
    )


def table_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [metric_block("overall", result)]
    scenarios = result.get("scenario_metrics") or {}
    for name in ("buying", "browsing", "intent_override", "boundary"):
        if name in scenarios:
            rows.append(metric_block(name, scenarios[name]))
    return rows


def previous_run(runs_dir: Path, current: Path) -> dict[str, Any] | None:
    candidates = sorted(p for p in runs_dir.glob("*.json") if p != current)
    if not candidates:
        return None
    try:
        return json.loads(candidates[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def print_table(result: dict[str, Any], prev: dict[str, Any] | None) -> None:
    prev_by_name = {row["name"]: row for row in table_rows(prev)} if prev else {}
    header = f"{'scope':16} {'HR@10':>9} {'MRR':>9} {'MTTC':>9} {'TechScore':>11} {'delta':>10}"
    print(header)
    print("-" * len(header))
    for row in table_rows(result):
        prior = prev_by_name.get(row["name"])
        score = row["recommended_technical_score"]
        delta = ""
        if prior:
            prev_score = prior["recommended_technical_score"]
            if score is not None and prev_score is not None:
                d = float(score) - float(prev_score)
                delta = f"{d:+.6f}"
        print(
            f"{row['name']:16} "
            f"{fmt(row['hit_rate_at_10']):>9} "
            f"{fmt(row['mrr']):>9} "
            f"{fmt(row['mttc']):>9} "
            f"{fmt(score):>11} "
            f"{delta:>10}"
        )
        if prior and score is not None and prior["recommended_technical_score"] is not None:
            if float(score) < float(prior["recommended_technical_score"]):
                print(f"  regression: {row['name']} score decreased")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluator with regression table")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", default="results.json")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--agent", default="starter.agent:Agent")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected sessions")
    parser.add_argument(
        "--scenario",
        choices=["buying", "browsing", "intent_override", "boundary"],
        default=None,
        help="Run only one scenario type",
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    dataset_path = Path(args.dataset)
    if not catalog_path.exists():
        raise SystemExit(f"missing catalog: {catalog_path}")
    if not dataset_path.exists():
        raise SystemExit(f"missing dataset: {dataset_path}")

    agent_cls = load_agent_class(args.agent)
    samples = load_jsonl(dataset_path)
    if args.scenario:
        samples = [sample for sample in samples if sample.get("scenario_type") == args.scenario]
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]
    print(f"selected sessions: {len(samples)}", flush=True)
    catalog_ids, categories, products = catalog_index(catalog_path)
    result = evaluate(agent_cls(catalog_path), samples, catalog_ids, categories, products)

    output = Path(args.output)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    runs_dir = Path(args.runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_agent = args.agent.replace(":", "_").replace(".", "_")
    run_path = runs_dir / f"{stamp}-{safe_agent}.json"
    shutil.copyfile(output, run_path)
    prev = previous_run(runs_dir, run_path)
    print_table(result, prev)
    print(f"\nwrote {output}")
    print(f"archived {run_path}")


if __name__ == "__main__":
    main()
