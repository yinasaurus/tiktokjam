"""Smoke ranking: exact-phrase route should surface the obvious target."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config
from agent.types import asins_of


def test_navy_cotton_tee_ranks_near_top(records, catalog):
    agent = Agent(
        catalog=records,
        config=Config(lexical_enabled=False, dense_enabled=False, exact_phrase_enabled=True),
    )
    agent.reset("s1", {})
    out = agent.respond("s1", "navy cotton crew neck t-shirt", turn=1, top_k=10)
    recs = asins_of(out)
    assert "B000000001" in recs[:5]
