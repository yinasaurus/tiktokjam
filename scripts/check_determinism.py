"""NFR-9 helper: run two identical sessions and compare recommendations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import Agent, Config

FIXTURE = ROOT / "tests" / "fixtures" / "catalog.jsonl"


def run(records, config):
    agent = Agent(catalog=records, config=config)
    agent.reset("s", {})
    return agent.respond("s", "navy cotton crew neck t-shirt", turn=1, top_k=10)


def main() -> int:
    records = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line]
    cfg = Config(lexical_enabled=False)
    a, b = run(records, cfg), run(records, cfg)
    if a["recommendations"] != b["recommendations"]:
        print("MISMATCH")
        print(a["recommendations"])
        print(b["recommendations"])
        return 1
    print("ok: identical recommendations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
