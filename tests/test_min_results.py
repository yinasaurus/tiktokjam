"""FR-2 / FR-23 — never return fewer than min(top_k, |catalog|) ASINs."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config


def test_overconstrained_still_returns_top_k(catalog, records):
    config = Config(
        lexical_enabled=False,
        dense_enabled=False,
        exact_phrase_enabled=True,
        K_exact=5,
        N_fuse=5,
    )
    agent = Agent(catalog=records, config=config)
    agent.reset("s1", {})
    out = agent.respond(
        "s1",
        "I want a purple sequin tuxedo made of cheese with fourteen sleeves",
        turn=1,
        top_k=10,
    )
    recs = out["recommendations"]
    assert len(recs) == min(10, len(catalog))
    assert len(recs) == len(set(recs))
    assert all(a in catalog.asin_to_idx for a in recs)


def test_recommendations_on_every_turn_including_question(records, catalog):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("s1", {})
    out = agent.respond("s1", "looking for cotton t-shirts", turn=1, top_k=10)
    assert len(out["recommendations"]) == min(10, len(catalog))
    assert out["usage"]["prompt_tokens"] >= 0
    assert out["usage"]["completion_tokens"] >= 0
    assert out["usage"]["total_tokens"] >= 0
    if out["ask_attribute"] is not None:
        assert out["ask_attribute"] in agent.config.ask_attributes
