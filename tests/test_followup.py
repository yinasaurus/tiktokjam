"""Short follow-up answers must change retrieval, not stick on popularity."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config
from agent.extract import ConstraintExtractor
from agent.state import SessionState
from agent.types import asins_of


def test_brown_extracts_as_color(catalog):
    ext = ConstraintExtractor(catalog, Config())
    state = SessionState("s", {})
    state.asked.append("color")
    hits = ext.extract("brown", state, turn=2)
    assert any(c.text == "brown" and c.attribute == "color" for c in hits)


def test_eu40_extracts_as_size(catalog):
    ext = ConstraintExtractor(catalog, Config())
    state = SessionState("s", {})
    hits = ext.extract("eu40", state, turn=2)
    assert any(c.attribute == "size" for c in hits)


def test_color_followup_changes_ranking(records):
    agent = Agent(
        catalog=records,
        config=Config(lexical_enabled=False, dense_enabled=False, exact_phrase_enabled=True),
    )
    agent.reset("s1", {})
    first = asins_of(agent.respond("s1", "cotton t-shirts", turn=1, top_k=10))
    second = asins_of(agent.respond("s1", "navy", turn=2, top_k=10))
    assert "B000000001" in second[:5]
    assert second != first or second[0] == "B000000001"
