"""One-turn smoke session against the fixture catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import Agent, Config

FIXTURE = ROOT / "tests" / "fixtures" / "catalog.jsonl"


def main() -> None:
    records = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line]
    agent = Agent(catalog=records, config=Config(lexical_enabled=False))
    agent.reset("demo", {"note": "fixture smoke"})
    turns = [
        "I'm looking for navy cotton t-shirts",
        "crew neck please",
        "regular fit is fine",
    ]
    for i, msg in enumerate(turns, start=1):
        out = agent.respond("demo", msg, turn=i, top_k=5)
        print(f"\n--- turn {i} ---")
        print("user:", msg)
        print("ask_attribute:", out["ask_attribute"])
        print("message:", out["message"])
        print("recommendations:")
        for asin in out["recommendations"]:
            product = agent.catalog.get(asin)
            title = product.title if product else "?"
            print(f"  {asin}  {title}")


if __name__ == "__main__":
    main()
