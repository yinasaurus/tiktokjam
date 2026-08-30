"""Train the LightGBM LambdaRank reranker from public-set sessions.

This is a local development tool. It writes a small model artifact to
models/ltr.txt, but it never writes catalog data or public-set contents.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import Agent
from agent.config import Config
from agent.rank_features import FEATURE_NAMES, feature_vector
from agent.types import asins_of
from evaluator.local_evaluator import (
    TOP_K,
    coarse_category,
    customer_reply,
    initial_message,
    catalog_index,
    load_jsonl,
    materialize_hidden_fields,
)


def stable_split(samples: list[dict], train_ratio: float) -> tuple[list[dict], list[dict]]:
    ordered = sorted(samples, key=lambda s: str(s.get("sample_id", "")))
    cut = max(1, min(len(ordered) - 1, round(len(ordered) * train_ratio)))
    return ordered[:cut], ordered[cut:]


def rows_for_samples(
    samples: list[dict],
    catalog_path: Path,
    categories: dict[str, list[str]],
    products: dict[str, dict],
    config: Config,
    candidates_per_turn: int,
) -> tuple[list[list[float]], list[int], list[int]]:
    features: list[list[float]] = []
    labels: list[int] = []
    groups: list[int] = []
    agent = Agent(catalog_path, config=replace(config, rerank_mode="heuristic"))

    for sample in samples:
        session_id = f"ltr_{uuid.uuid4().hex}"
        agent.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        intent_card, behavior = materialize_hidden_fields(sample, products)
        effective_sample = {**sample, "intent_card": intent_card, "behavior": behavior}
        disclosed: set[str] = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        user_message = initial_message(effective_sample, coarse_category(categories.get(target, [])), disclosed)

        for turn in range(1, 11):
            response = agent.respond(session_id, user_message, turn, max(TOP_K, candidates_per_turn))
            state = agent._sessions[session_id]
            constraints = agent._state_mgr.active_constraints(state)
            ranked = asins_of(response)[:candidates_per_turn]
            if target in ranked:
                group_start = len(labels)
                for rank, asin in enumerate(ranked, start=1):
                    fused_proxy = 1.0 / rank
                    features.append(feature_vector(asin, fused_proxy, agent.catalog, state, constraints, config))
                    labels.append(1 if asin == target else 0)
                groups.append(len(labels) - group_start)

            if override_applied and target in ranked[:TOP_K]:
                break
            if turn == 10:
                break

            override = effective_sample.get("behavior", {}).get("override") or {}
            if not override_applied and turn + 1 == int(override.get("turn", 3)):
                override_applied = True
                new_value = str(override.get("new_value", ""))
                if new_value:
                    disclosed.add(new_value)
                user_message = str(override.get("message", "Actually, please ignore my earlier preference."))
            else:
                user_message, boundary_used = customer_reply(
                    effective_sample, response.get("ask_attribute"), disclosed, boundary_used
                )

    return features, labels, groups


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LightGBM LambdaRank reranker")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--dataset", type=Path, default=Path("data/public_set.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("models/ltr.txt"))
    parser.add_argument("--metadata", type=Path, default=Path("models/ltr_metadata.json"))
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--candidates-per-turn", type=int, default=50)
    parser.add_argument("--limit", type=int, default=None, help="Train from only the first N selected sessions")
    parser.add_argument(
        "--scenario",
        choices=["buying", "browsing", "intent_override", "boundary"],
        default=None,
        help="Train from only one scenario type",
    )
    args = parser.parse_args()

    if not args.catalog.exists():
        raise SystemExit(f"missing catalog: {args.catalog}")
    if not args.dataset.exists():
        raise SystemExit(f"missing dataset: {args.dataset}")

    try:
        import lightgbm as lgb
        import numpy as np
    except Exception as exc:
        raise SystemExit(f"LightGBM/numpy import failed: {exc}") from exc

    random.seed(0)
    print(f"loading dataset: {args.dataset}", flush=True)
    samples = load_jsonl(args.dataset)
    if args.scenario:
        samples = [sample for sample in samples if sample.get("scenario_type") == args.scenario]
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]
    print(f"selected sessions: {len(samples)}", flush=True)
    print(f"loading catalog index: {args.catalog}", flush=True)
    _, categories, products = catalog_index(args.catalog)
    train_samples, holdout_samples = stable_split(samples, args.train_ratio)
    config = Config()

    print(f"generating train rows from {len(train_samples)} sessions", flush=True)
    x_train, y_train, group_train = rows_for_samples(
        train_samples, args.catalog, categories, products, config, args.candidates_per_turn
    )
    print(f"generating holdout rows from {len(holdout_samples)} sessions", flush=True)
    x_holdout, y_holdout, group_holdout = rows_for_samples(
        holdout_samples, args.catalog, categories, products, config, args.candidates_per_turn
    )
    if not x_train or not group_train:
        raise SystemExit("no positive training groups generated; inspect candidate recall before training")

    ranker = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=120,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=5,
        random_state=0,
        deterministic=True,
        verbosity=-1,
    )
    fit_kwargs = {
        "X": np.asarray(x_train, dtype=np.float32),
        "y": np.asarray(y_train, dtype=np.int32),
        "group": group_train,
        "feature_name": list(FEATURE_NAMES),
    }
    if x_holdout and group_holdout:
        fit_kwargs["eval_set"] = [(np.asarray(x_holdout, dtype=np.float32), np.asarray(y_holdout, dtype=np.int32))]
        fit_kwargs["eval_group"] = [group_holdout]
    ranker.fit(**fit_kwargs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ranker.booster_.save_model(str(args.output))
    metadata = {
        "feature_names": FEATURE_NAMES,
        "train_samples": len(train_samples),
        "holdout_samples": len(holdout_samples),
        "train_groups": len(group_train),
        "holdout_groups": len(group_holdout),
        "train_rows": len(y_train),
        "holdout_rows": len(y_holdout),
        "positives": int(sum(y_train)),
        "candidates_per_turn": args.candidates_per_turn,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.output), **metadata}, indent=2))


if __name__ == "__main__":
    main()
