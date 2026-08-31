"""Deterministic fixture-customer gate for hosted CI.

This does not replace the official public-set evaluator. It gives CI a cheap
customer-like check using only committed fixture data, while the real release
gate remains `scripts/check_acceptance.py --threshold 0.80` on local official
data.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.fast_agent import coarse_category, intent_card
from agent.types import asins_of
from starter.agent import Agent


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _opening(product: dict[str, Any], rng: random.Random, disclosed: set[str]) -> tuple[str, list[str]]:
    categories = [str(item) for item in product.get("categories") or []]
    category = coarse_category(categories)
    card = intent_card(product)
    constraints = []
    for value in [*card["hard_constraints"], *card["soft_preferences"]]:
        text = str(value).strip()
        if text and text not in constraints:
            constraints.append(text)
    if constraints and rng.random() < 0.5:
        disclosed.add(constraints[0])
        return f"I'm looking for {category}. A key requirement is: {constraints[0]}.", constraints
    return f"I'm looking for {category}, but I'm still exploring.", constraints


def _reply(ask_attribute: str | None, constraints: list[str], disclosed: set[str]) -> str:
    remaining = [value for value in constraints if value not in disclosed]
    if not remaining:
        return f"I don't have an additional preference for {ask_attribute or 'other'}."
    values = remaining[:2]
    disclosed.update(values)
    return f"For that, what matters is: {'; '.join(values)}."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixture synthetic customer acceptance gate")
    parser.add_argument("--catalog", type=Path, default=Path("tests/fixtures/catalog.jsonl"))
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args()

    products = _load_jsonl(args.catalog)
    if not products:
        raise SystemExit(f"empty catalog: {args.catalog}")

    rng = random.Random(args.seed)
    agent = Agent(args.catalog)
    hits = 0
    reciprocal_rank = 0.0
    total_turns = 0
    misses: list[dict[str, str]] = []
    for trial in range(args.trials):
        target = rng.choice(products)
        target_asin = str(target["parent_asin"])
        session_id = f"synthetic-{trial:04d}"
        disclosed: set[str] = set()
        message, constraints = _opening(target, rng, disclosed)
        agent.reset(session_id, {})
        hit = False
        first_message = message
        for turn in range(1, 11):
            out = agent.respond(session_id, message, turn=turn, top_k=10)
            ranked = asins_of(out)
            if target_asin in ranked[:10]:
                rank = ranked[:10].index(target_asin) + 1
                hits += 1
                reciprocal_rank += 1.0 / rank
                total_turns += turn
                hit = True
                break
            message = _reply(out.get("ask_attribute"), constraints, disclosed)
        if not hit:
            total_turns += 11
            misses.append({"target": target_asin, "message": first_message})

    hit_rate = hits / max(args.trials, 1)
    mrr = reciprocal_rank / max(args.trials, 1)
    mttc = total_turns / max(args.trials, 1)
    summary = {
        "threshold": args.threshold,
        "passed": hit_rate >= args.threshold,
        "catalog": str(args.catalog),
        "trials": args.trials,
        "seed": args.seed,
        "hit_rate_at_10": round(hit_rate, 6),
        "mrr": round(mrr, 6),
        "mttc": round(mttc, 6),
        "misses": misses[:10],
    }
    print(json.dumps(summary, indent=2))
    if hit_rate < args.threshold:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
