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
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.fast_agent import coarse_category
from agent.types import asins_of
from starter.agent import Agent

WORD_RE = re.compile(r"[a-z0-9]+", re.I)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _details(product: dict[str, Any]) -> dict[str, Any]:
    value = product.get("details")
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _message(product: dict[str, Any], rng: random.Random) -> str:
    details = _details(product)
    categories = [str(item) for item in product.get("categories") or []]
    leaf = categories[-1] if categories else "clothing item"
    category = coarse_category(categories)
    title = str(product.get("title") or leaf)
    features = [str(item) for item in product.get("features") or []]
    color = str(details.get("Color") or "").strip()
    material = str(details.get("Material") or "").strip()
    tokens = WORD_RE.findall(title.lower())
    title_hint = " ".join(tokens[:4]) if tokens else leaf
    feature = features[0] if features else title_hint

    templates = [
        f"{color} {material} {leaf}".strip(),
        f"I'm looking for {category}. A key requirement is: {feature}.",
        f"I need {title_hint}",
        f"{feature} {leaf}",
        f"I'm looking for {category}, but I'm still exploring.",
    ]
    return rng.choice([item for item in templates if item.strip()])


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
    misses: list[dict[str, str]] = []
    for trial in range(args.trials):
        target = rng.choice(products)
        target_asin = str(target["parent_asin"])
        session_id = f"synthetic-{trial:04d}"
        message = _message(target, rng)
        agent.reset(session_id, {})
        out = agent.respond(session_id, message, turn=1, top_k=10)
        ranked = asins_of(out)
        if target_asin in ranked[:10]:
            hits += 1
        else:
            misses.append({"target": target_asin, "message": message})

    hit_rate = hits / max(args.trials, 1)
    summary = {
        "threshold": args.threshold,
        "passed": hit_rate >= args.threshold,
        "catalog": str(args.catalog),
        "trials": args.trials,
        "seed": args.seed,
        "hit_rate_at_10": round(hit_rate, 6),
        "misses": misses[:10],
    }
    print(json.dumps(summary, indent=2))
    if hit_rate < args.threshold:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
