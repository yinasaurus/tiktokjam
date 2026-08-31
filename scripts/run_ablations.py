"""Run public-set route/rerank ablations and write reproducible summaries.

Requires local-only data files:
    data/catalog.jsonl
    data/public_set.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import Agent
from agent.config import Config
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl


VARIANTS = {
    "full": {},
    "no_exact_phrase": {"exact_phrase_enabled": False},
    "no_dense": {"dense_enabled": False},
    "no_rerank": {"rerank_mode": "off"},
    "lexical_only": {
        "exact_phrase_enabled": False,
        "dense_enabled": False,
        "rerank_mode": "off",
    },
    "ltr": {"rerank_mode": "ltr"},
    "cascade": {"rerank_mode": "cascade"},
}


def compact(result: dict) -> dict:
    keys = (
        "sample_count",
        "hit_rate_at_10",
        "mrr",
        "mttc",
        "efficiency",
        "recommended_technical_score",
        "reported_token_usage",
        "scenario_metrics",
    )
    return {key: result[key] for key in keys if key in result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TechJam public-set ablations")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--dataset", type=Path, default=Path("data/public_set.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("eval_output"))
    parser.add_argument(
        "--ltr-model",
        type=Path,
        default=None,
        help="Optional LightGBM model path for ltr/cascade research runs.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected sessions")
    parser.add_argument(
        "--scenario",
        choices=["buying", "browsing", "intent_override", "boundary"],
        default=None,
        help="Run only one scenario type",
    )
    parser.add_argument("--progress-every", type=int, default=1, help="Print before every N variants")
    parser.add_argument(
        "--variant",
        action="append",
        choices=sorted(VARIANTS),
        help="Variant to run. Repeatable. Defaults to all variants except ltr/cascade when no model exists.",
    )
    args = parser.parse_args()

    if not args.catalog.exists():
        raise SystemExit(f"missing catalog: {args.catalog}")
    if not args.dataset.exists():
        raise SystemExit(f"missing dataset: {args.dataset}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"loading dataset: {args.dataset}", flush=True)
    samples = load_jsonl(args.dataset)
    if args.scenario:
        samples = [sample for sample in samples if sample.get("scenario_type") == args.scenario]
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]
    print(f"selected sessions: {len(samples)}", flush=True)
    print(f"loading catalog index: {args.catalog}", flush=True)
    catalog_ids, categories, products = catalog_index(args.catalog)

    selected = args.variant or ["full", "no_exact_phrase", "no_dense", "no_rerank", "lexical_only"]
    ltr_path = args.ltr_model or Path(Config().ltr_model_path)
    if args.variant is None and ltr_path.exists():
        selected.extend(["ltr", "cascade"])

    summaries: dict[str, dict] = {}
    for i, name in enumerate(selected, start=1):
        if args.progress_every > 0 and (i == 1 or i % args.progress_every == 0):
            print(f"running variant {i}/{len(selected)}: {name}", flush=True)
        config = replace(Config(), **VARIANTS[name])
        if args.ltr_model is not None:
            config = replace(config, ltr_model_path=str(args.ltr_model))
        agent = Agent(args.catalog, config=config)
        result = evaluate(agent, samples, catalog_ids, categories, products)
        summaries[name] = compact(result)
        suffix = []
        if args.scenario:
            suffix.append(args.scenario)
        if args.limit is not None:
            suffix.append(f"n{len(samples)}")
        stem = name if not suffix else f"{name}-{'-'.join(suffix)}"
        out_path = args.output_dir / f"{stem}.json"
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        score = summaries[name].get("recommended_technical_score")
        hit = summaries[name].get("hit_rate_at_10")
        print(f"{name:16} score={score} hit@10={hit} -> {out_path}")

    summary_name = "ablation_summary" if not args.scenario else f"ablation_summary-{args.scenario}"
    if args.limit is not None:
        summary_name += f"-n{len(samples)}"
    summary_path = args.output_dir / f"{summary_name}.json"
    summary_path.write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    print(f"summary -> {summary_path}")


if __name__ == "__main__":
    main()
