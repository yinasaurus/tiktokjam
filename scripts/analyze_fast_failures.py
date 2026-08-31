"""Diagnose FastAgent misses/ranks without modifying the official evaluator."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator.local_evaluator import (  # noqa: E402
    MAX_TURNS,
    TOP_K,
    coarse_category,
    customer_reply,
    initial_message,
    catalog_index,
    load_jsonl,
    materialize_hidden_fields,
)
from starter.agent import Agent  # noqa: E402


def full_rank(agent: Agent, session_id: str, top_k: int = 50000) -> list[str]:
    state = agent.sessions[session_id]
    pool = state["pool"] or list(agent.products.keys())
    return agent._rank(state, pool, top_k)  # type: ignore[attr-defined]


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose FastAgent public-set failures")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--dataset", type=Path, default=Path("data/public_set.jsonl"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--show", type=int, default=25)
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    if args.limit is not None:
        samples = samples[: max(0, args.limit)]
    catalog_ids, categories, products = catalog_index(args.catalog)
    agent = Agent(args.catalog)

    rows: list[dict[str, Any]] = []
    first_hit_ranks: list[int] = []
    missed = 0
    for sample in samples:
        session_id = f"diag_{uuid.uuid4().hex}"
        agent.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, products)
        effective = {**sample, "intent_card": card, "behavior": behavior}
        disclosed: set[str] = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        user_message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)
        hit_turn: int | None = None
        hit_rank: int | None = None
        target_full_rank: int | None = None
        last_constraints: list[str] = []
        last_pool_size = 0
        turns: list[str] = []

        for turn in range(1, MAX_TURNS + 1):
            turns.append(user_message)
            response = agent.respond(session_id, user_message, turn, TOP_K)
            ranked = [
                str(item.get("parent_asin", "")).strip()
                for item in response.get("recommendations", [])
                if isinstance(item, dict) and str(item.get("parent_asin", "")).strip() in catalog_ids
            ][:TOP_K]
            ordered = full_rank(agent, session_id)
            state = agent.sessions[session_id]
            last_constraints = list(state["constraints"])
            last_pool_size = len(state["pool"] or agent.products)
            if target in ordered:
                target_full_rank = ordered.index(target) + 1
            else:
                target_full_rank = None
            if override_applied and target in ranked:
                hit_turn = turn
                hit_rank = ranked.index(target) + 1
                first_hit_ranks.append(hit_rank)
                break
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

        if hit_turn is None:
            missed += 1
        rows.append(
            {
                "sample_id": sample["sample_id"],
                "scenario": sample["scenario_type"],
                "hit_turn": hit_turn,
                "hit_rank": hit_rank,
                "target_full_rank": target_full_rank,
                "pool_size": last_pool_size,
                "constraints": last_constraints,
                "target": target,
                "target_title": products[target].get("title"),
                "turns": turns,
            }
        )

    scenario_counts = Counter(row["scenario"] for row in rows)
    miss_counts = Counter(row["scenario"] for row in rows if row["hit_turn"] is None)
    rank_counts = Counter(row["hit_rank"] for row in rows if row["hit_rank"] is not None)
    full_rank_buckets = defaultdict(int)
    for row in rows:
        rank = row["target_full_rank"]
        if rank is None:
            full_rank_buckets["not_in_pool"] += 1
        elif rank <= 1:
            full_rank_buckets["rank_1"] += 1
        elif rank <= 10:
            full_rank_buckets["rank_2_10"] += 1
        elif rank <= 50:
            full_rank_buckets["rank_11_50"] += 1
        else:
            full_rank_buckets["rank_gt_50"] += 1

    print(
        json.dumps(
            {
                "sample_count": len(rows),
                "missed": missed,
                "scenario_counts": scenario_counts,
                "miss_counts": miss_counts,
                "hit_rank_counts": rank_counts,
                "target_full_rank_buckets_at_end": dict(sorted(full_rank_buckets.items())),
                "worst_rows": sorted(
                    rows,
                    key=lambda row: (
                        row["hit_turn"] is not None,
                        row["target_full_rank"] if row["target_full_rank"] is not None else 999999,
                    ),
                )[: args.show],
            },
            indent=2,
            default=dict,
        )
    )


if __name__ == "__main__":
    main()
