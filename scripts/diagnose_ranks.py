"""One-pass rank/recall diagnosis on the public 200. Does not change FastAgent."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


class ProbeAgent:
    def __init__(self, inner: Agent, targets: dict[str, str]) -> None:
        self.inner = inner
        self.targets = targets
        self._sid_to_sample: dict[str, str] = {}
        self.rows: list[dict] = []

    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        self.inner.reset(session_id, user_profile)

    def bind(self, session_id: str, sample_id: str) -> None:
        self._sid_to_sample[session_id] = sample_id

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int = 10) -> dict:
        response = self.inner.respond(session_id, user_message, turn, top_k)
        sample_id = self._sid_to_sample.get(session_id, "")
        target = self.targets.get(sample_id, "")
        state = self.inner.sessions[session_id]
        pool = state["pool"]
        pool_list = pool if pool is not None else list(self.inner.products.keys())
        in_pool = target in set(pool_list) if pool is not None else True
        full = self.inner._rank(state, pool_list, top_k=min(500, len(pool_list)))
        try:
            pool_rank = full.index(target) + 1
        except ValueError:
            pool_rank = None
        recs = [
            str(item.get("parent_asin") or "")
            for item in (response.get("recommendations") or [])
            if isinstance(item, dict)
        ]
        try:
            shown_rank = recs.index(target) + 1
        except ValueError:
            shown_rank = None
        self.rows.append(
            {
                "sample_id": sample_id,
                "turn": turn,
                "pool_size": len(pool_list),
                "in_pool": in_pool,
                "pool_rank": pool_rank,
                "shown_rank": shown_rank,
            }
        )
        return response


def main() -> None:
    samples = load_jsonl(ROOT / "data" / "public_set.jsonl")
    targets = {s["sample_id"]: str(s["ground_truth"]["parent_asin"]) for s in samples}
    catalog_ids, categories, products = catalog_index(ROOT / "data" / "catalog.jsonl")
    inner = Agent(ROOT / "data" / "catalog.jsonl")
    probe = ProbeAgent(inner, targets)

    orig_reset = probe.reset

    def reset_and_bind(session_id: str, user_profile: dict | None = None) -> None:
        orig_reset(session_id, user_profile)
        # evaluate() does not tell us sample_id at reset; bind latest unused sample
        # instead wrap evaluate loop ourselves for binding.

    # Use evaluate() for official metrics, then replay probe via a custom loop.
    from evaluator.local_evaluator import (
        MAX_TURNS,
        TOP_K,
        coarse_category,
        customer_reply,
        initial_message,
        materialize_hidden_fields,
        metric_summary,
        normalize_recommendations,
    )
    import uuid
    from collections import defaultdict

    sessions = []
    for sample in samples:
        session_id = f"diag_{uuid.uuid4().hex}"
        probe.bind(session_id, sample["sample_id"])
        probe.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, products)
        effective = {**sample, "intent_card": card, "behavior": behavior}
        disclosed: set[str] = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        user_message = initial_message(
            effective, coarse_category(categories.get(target, [])), disclosed
        )
        hit_turn = None
        best_rank = None
        ever_in_pool = False
        best_pool_rank = None
        last_pool_size = None
        for turn in range(1, MAX_TURNS + 1):
            response = probe.respond(session_id, user_message, turn, TOP_K)
            ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
            rec = probe.rows[-1]
            last_pool_size = rec["pool_size"]
            if rec["in_pool"]:
                ever_in_pool = True
            if rec["pool_rank"] is not None:
                if best_pool_rank is None or rec["pool_rank"] < best_pool_rank:
                    best_pool_rank = rec["pool_rank"]
            if override_applied and target in ranked:
                best_rank = ranked.index(target) + 1
                hit_turn = turn
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
        sessions.append(
            {
                "sample_id": sample["sample_id"],
                "scenario_type": sample["scenario_type"],
                "difficulty_bucket": sample.get("difficulty_bucket"),
                "category_bucket": sample.get("category_bucket"),
                "hit": hit_turn is not None,
                "first_hit_turn": hit_turn,
                "best_rank": best_rank,
                "reciprocal_rank": 0.0 if best_rank is None else 1.0 / best_rank,
                "ever_in_pool": ever_in_pool,
                "best_pool_rank": best_pool_rank,
                "last_pool_size": last_pool_size,
            }
        )

    overall = metric_summary(sessions)
    efficiency = max(0.0, min(1.0, (11.0 - float(overall["mttc"])) / 10.0))
    technical = round(0.50 * overall["hit_rate_at_10"] + 0.30 * overall["mrr"] + 0.20 * efficiency, 6)

    hits = [s for s in sessions if s["hit"]]
    misses = [s for s in sessions if not s["hit"]]
    rank1 = sum(1 for s in hits if s["best_rank"] == 1)
    rank23 = sum(1 for s in hits if s["best_rank"] in (2, 3))
    rank410 = sum(1 for s in hits if s["best_rank"] is not None and 4 <= s["best_rank"] <= 10)

    miss_scenario = Counter(s["scenario_type"] for s in misses)
    miss_diff = Counter(s["difficulty_bucket"] for s in misses)
    miss_in_pool = sum(1 for s in misses if s["ever_in_pool"])
    miss_not_in_pool = sum(1 for s in misses if not s["ever_in_pool"])
    miss_pool_ranks = [s["best_pool_rank"] for s in misses if s["best_pool_rank"] is not None]
    hit_not_r1 = [s for s in hits if s["best_rank"] != 1]

    out = {
        "official": {
            **overall,
            "efficiency": round(efficiency, 6),
            "recommended_technical_score": technical,
        },
        "rank_distribution_hits": {
            "n_hits": len(hits),
            "rank_1": rank1,
            "rank_2_3": rank23,
            "rank_4_10": rank410,
        },
        "misses": {
            "count": len(misses),
            "by_scenario": dict(miss_scenario),
            "by_difficulty": dict(miss_diff),
            "ever_in_pool": miss_in_pool,
            "never_in_pool": miss_not_in_pool,
            "best_pool_ranks": miss_pool_ranks,
            "sample_ids": [s["sample_id"] for s in misses],
        },
        "ranking_headroom": {
            "hits_not_rank_1": len(hit_not_r1),
            "mean_rank_of_hits": round(sum(s["best_rank"] for s in hits) / max(len(hits), 1), 4),
        },
    }
    print(json.dumps(out, indent=2))
    (ROOT / "eval_output").mkdir(exist_ok=True)
    (ROOT / "eval_output" / "rank_diagnosis.json").write_text(
        json.dumps({"summary": out, "sessions": sessions}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
