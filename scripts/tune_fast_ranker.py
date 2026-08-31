"""Compare FastAgent rank formulas from one deterministic dialog replay.

This is a research helper, not the submitted agent. It keeps the ask policy and
state transitions fixed, then asks: if we changed only the product tie-break
formula, would public-set MRR or TechnicalScore improve?
"""

from __future__ import annotations

import argparse
import math
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agent.fast_agent as fast  # noqa: E402
from evaluator.local_evaluator import (  # noqa: E402
    MAX_TURNS,
    TOP_K,
    coarse_category,
    catalog_index,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
)
from starter.agent import Agent  # noqa: E402


Snapshot = dict[str, Any]


def build_snapshots(samples: list[dict], categories: dict[str, list[str]], products: dict[str, dict]) -> tuple[Agent, list[dict]]:
    agent = Agent("data/catalog.jsonl")
    rows: list[dict[str, Any]] = []
    for sample in samples:
        session_id = f"tune_{uuid.uuid4().hex}"
        agent.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, products)
        effective = {**sample, "intent_card": card, "behavior": behavior}
        disclosed: set[str] = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        user_message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
        snapshots: list[Snapshot] = []

        for turn in range(1, MAX_TURNS + 1):
            response = agent.respond(session_id, user_message, turn, TOP_K)
            state = agent.sessions[session_id]
            snapshots.append(
                {
                    "turn": turn,
                    "override_applied": override_applied,
                    "pool": tuple(state["pool"] or agent.products.keys()),
                    "constraints": tuple(state["constraints"]),
                    "vocab": tuple(sorted(state["vocab"])),
                }
            )
            if turn == MAX_TURNS:
                break

            override = effective.get("behavior", {}).get("override") or {}
            if not override_applied and turn + 1 == int(override.get("turn", 3)):
                override_applied = True
                new_value = str(override.get("new_value", ""))
                if new_value:
                    disclosed.add(new_value)
                user_message = str(override.get("message", "Actually, please ignore my earlier preference."))
            else:
                user_message, boundary_used = customer_reply(
                    effective, response.get("ask_attribute"), disclosed, boundary_used
                )

        rows.append(
            {
                "sample_id": sample["sample_id"],
                "scenario": sample["scenario_type"],
                "target": target,
                "snapshots": snapshots,
            }
        )
    return agent, rows


def build_rank_context(agent: Agent) -> dict[str, Any]:
    pop_rank = {pid: rank for rank, pid in enumerate(agent.popularity)}
    constraint_pos: dict[tuple[str, str], int] = {}
    search_texts: dict[str, str] = {}
    for pid, product in agent.products.items():
        text = fast.searchable_text(product).lower()
        search_texts[pid] = text
        card = fast.intent_card(product, corpus=text)
        seen: set[str] = set()
        values: list[str] = []
        for value in [*card.get("hard_constraints", ()), *card.get("soft_preferences", ())]:
            if value and value not in seen:
                seen.add(str(value))
                values.append(str(value))
        for idx, value in enumerate(values):
            constraint_pos[(pid, value)] = idx
    return {
        "pop_rank": pop_rank,
        "constraint_pos": constraint_pos,
        "search_texts": search_texts,
    }


def rank_snapshot(agent: Agent, ctx: dict[str, Any], snap: Snapshot, variant: str) -> list[str]:
    constraints = list(snap["constraints"])
    vocab = set(snap["vocab"])
    scored: list[tuple[float, str]] = []
    for pid in snap["pool"]:
        exact_sum = 0.0
        exact_count = 0
        pos_good = 0
        pos_distance = 0
        phrase_text = 0
        for obs_idx, constraint in enumerate(constraints):
            matches = agent.by_constraint.get(constraint, ())
            if pid in matches:
                exact_count += 1
                exact_sum += 20.0 / max(len(matches), 1)
                pos = ctx["constraint_pos"].get((pid, constraint))
                if pos is not None:
                    if pos == obs_idx:
                        pos_good += 1
                    pos_distance += abs(pos - obs_idx)
            if constraint.lower() in ctx["search_texts"].get(pid, ""):
                phrase_text += 1

        overlap = len(agent.tokens.get(pid, set()) & vocab)
        product = agent.products.get(pid, {})
        try:
            rating_count = float(product.get("rating_number") or 0)
        except (TypeError, ValueError):
            rating_count = 0.0
        try:
            avg_rating = float(product.get("average_rating") or 0)
        except (TypeError, ValueError):
            avg_rating = 0.0
        pop = math.log1p(max(0.0, rating_count))
        pop_rank = ctx["pop_rank"].get(pid, 999999)

        if variant == "current":
            score = exact_sum + 0.05 * overlap
        elif variant == "count_first":
            score = 10.0 * exact_count + exact_sum + 0.05 * overlap
        elif variant == "position":
            score = exact_sum + 0.50 * pos_good - 0.05 * pos_distance + 0.05 * overlap
        elif variant == "phrase_text":
            score = exact_sum + 0.20 * phrase_text + 0.05 * overlap
        elif variant == "pop_tiny":
            score = exact_sum + 0.05 * overlap + 0.01 * pop + 0.01 * avg_rating
        elif variant == "pop_small":
            score = exact_sum + 0.05 * overlap + 0.05 * pop + 0.02 * avg_rating
        elif variant == "pop_rank_tiny":
            score = exact_sum + 0.05 * overlap - 0.000001 * pop_rank
        elif variant == "count_pop":
            score = 10.0 * exact_count + exact_sum + 0.05 * overlap + 0.05 * pop + 0.02 * avg_rating
        elif variant == "position_pop":
            score = exact_sum + 0.50 * pos_good - 0.05 * pos_distance + 0.05 * overlap + 0.05 * pop
        elif variant == "all_features":
            score = (
                10.0 * exact_count
                + exact_sum
                + 0.50 * pos_good
                - 0.05 * pos_distance
                + 0.20 * phrase_text
                + 0.05 * overlap
                + 0.03 * pop
                + 0.01 * avg_rating
            )
        else:
            raise ValueError(f"Unknown variant: {variant}")
        scored.append((score, str(pid)))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [pid for _, pid in scored[:TOP_K]]


def metrics_for(agent: Agent, ctx: dict[str, Any], rows: list[dict], variant: str) -> dict[str, Any]:
    sessions: list[dict[str, Any]] = []
    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    hit_ranks: Counter[int] = Counter()
    misses: Counter[str] = Counter()

    for row in rows:
        first_turn = 11
        best_rank: int | None = None
        for snap in row["snapshots"]:
            ranked = rank_snapshot(agent, ctx, snap, variant)
            if snap["override_applied"] and row["target"] in ranked:
                first_turn = int(snap["turn"])
                best_rank = ranked.index(row["target"]) + 1
                hit_ranks[best_rank] += 1
                break
        item = {
            "scenario": row["scenario"],
            "hit": best_rank is not None,
            "turn": first_turn,
            "rank": best_rank,
            "rr": 0.0 if best_rank is None else 1.0 / best_rank,
        }
        sessions.append(item)
        by_scenario[row["scenario"]].append(item)
        if best_rank is None:
            misses[row["scenario"]] += 1

    return {
        **aggregate(sessions),
        "hit_rank_counts": dict(sorted(hit_ranks.items())),
        "miss_counts": dict(sorted(misses.items())),
        "scenario_metrics": {k: aggregate(v) for k, v in sorted(by_scenario.items())},
    }


def aggregate(items: list[dict[str, Any]]) -> dict[str, float]:
    if not items:
        return {"hit_rate_at_10": 0.0, "mrr": 0.0, "mttc": 0.0, "technical_score": 0.0}
    n = len(items)
    hr = sum(1 for item in items if item["hit"]) / n
    mrr = sum(float(item["rr"]) for item in items) / n
    mttc = sum(int(item["turn"]) for item in items) / n
    efficiency = max(0.0, min(1.0, (11.0 - mttc) / 10.0))
    score = 0.50 * hr + 0.30 * mrr + 0.20 * efficiency
    return {
        "hit_rate_at_10": hr,
        "mrr": mrr,
        "mttc": mttc,
        "technical_score": score,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune public-set FastAgent tie-breaks")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--dataset", type=Path, default=Path("data/public_set.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--variant",
        action="append",
        dest="variants",
        default=None,
        help="Variant to test. Repeatable. Defaults to all built-in variants.",
    )
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]
    _, categories, products = catalog_index(args.catalog)
    # Keep the submitted ask schedule fixed. Use this script for rank-only
    # experiments; ask schedule tests should use the official evaluator.
    agent, rows = build_snapshots(samples, categories, products)
    ctx = build_rank_context(agent)
    variants = args.variants or [
        "current",
        "count_first",
        "position",
        "phrase_text",
        "pop_tiny",
        "pop_small",
        "pop_rank_tiny",
        "count_pop",
        "position_pop",
        "all_features",
    ]

    print(f"{'variant':<16}{'HR@10':>9}{'MRR':>10}{'MTTC':>9}{'TechScore':>11}  misses")
    print("-" * 76)
    for variant in variants:
        result = metrics_for(agent, ctx, rows, variant)
        print(
            f"{variant:<16}"
            f"{result['hit_rate_at_10']:>9.3f}"
            f"{result['mrr']:>10.6f}"
            f"{result['mttc']:>9.3f}"
            f"{result['technical_score']:>11.6f}  "
            f"{result['miss_counts']}"
        )


if __name__ == "__main__":
    main()
