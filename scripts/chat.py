"""Interactive terminal chat. Uses data/catalog.jsonl when present."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import Agent, Config
from agent.types import asins_of

FIXTURE = ROOT / "tests" / "fixtures" / "catalog.jsonl"
OFFICIAL = ROOT / "data" / "catalog.jsonl"


def _catalog_path() -> Path:
    env = os.environ.get("SHOPPING_AGENT_CATALOG")
    if env:
        return Path(env)
    if OFFICIAL.exists():
        return OFFICIAL
    return FIXTURE


def main() -> None:
    path = _catalog_path()
    official = path.resolve() == OFFICIAL.resolve()
    config = Config() if official else Config(lexical_enabled=False)
    print(f"catalog: {path}")
    agent = Agent(catalog=path, config=config)
    session_id = "chat"
    agent.reset(session_id, {})
    turn = 1
    print("Type a message, or: reset / quit")
    print()
    while True:
        try:
            msg = input(f"you [{turn}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue
        lower = msg.lower()
        if lower in {"quit", "exit", "q"}:
            break
        if lower == "reset":
            agent.reset(session_id, {})
            turn = 1
            print("(session reset)\n")
            continue
        out = agent.respond(session_id, msg, turn=turn, top_k=5)
        print(f"  {out['message']}")
        if out["ask_attribute"]:
            print(f"  ask: {out['ask_attribute']}")
        for i, asin in enumerate(asins_of(out), start=1):
            product = agent.catalog.get(asin)
            title = product.title if product else asin
            print(f"  {i}. {title}")
        print()
        turn += 1


if __name__ == "__main__":
    main()
