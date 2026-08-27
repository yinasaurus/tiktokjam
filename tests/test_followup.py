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


def test_male_extracts_as_style(catalog):
    ext = ConstraintExtractor(catalog, Config())
    hits = ext.extract("male", SessionState("s", {}), turn=2)
    assert any(c.text == "men" and c.attribute == "department" for c in hits)
    assert not any(c.source == "category" for c in hits)


def test_for_him_and_her_extract_gender(catalog):
    ext = ConstraintExtractor(catalog, Config())
    him = ext.extract("for him", SessionState("s", {}), turn=2)
    her = ext.extract("for her", SessionState("s", {}), turn=2)
    assert any(c.text == "men" and c.attribute == "department" for c in him)
    assert any(c.text == "women" and c.attribute == "department" for c in her)


def test_blouse_maps_to_catalog_leaf(catalog):
    ext = ConstraintExtractor(catalog, Config())
    blouse = [c.text for c in ext.extract("blouse", SessionState("s", {}), 1) if c.source == "category"]
    assert blouse
    assert "blouse" in blouse[0]


def test_shirt_does_not_bind_blouse_category(catalog):
    ext = ConstraintExtractor(catalog, Config())
    hits = ext.extract("blue shirt", SessionState("s", {}), turn=1)
    cats = [c.text for c in hits if c.source == "category"]
    assert cats
    assert "blouse" not in cats[0]
    assert cats[0] in {"t-shirts", "shirts", "t-shirt", "shirt"}


def test_male_followup_ranks_mens_above_womens_blouse(records):
    agent = Agent(
        catalog=records,
        config=Config(lexical_enabled=False, dense_enabled=False, exact_phrase_enabled=True),
    )
    agent.reset("s1", {})
    agent.respond("s1", "blue shirt", turn=1, top_k=10)
    recs = asins_of(agent.respond("s1", "male", turn=2, top_k=10))
    assert recs[0] != "B000000013"
    assert "B000000013" not in recs[:5]
    assert recs[0] in {"B000000001", "B000000002", "B000000003", "B000000007", "B000000009"}
