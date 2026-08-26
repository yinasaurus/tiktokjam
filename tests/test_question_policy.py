"""Don't re-ask category (or any slot we already filled)."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config
from agent.extract import ConstraintExtractor
from agent.question import choose_ask_attribute
from agent.state import SessionState
from agent.types import SlotValue


def test_does_not_ask_category_when_leaf_known(catalog, config):
    state = SessionState("s", {})
    state.leaf_category = "t-shirts"
    state.slots["color"] = SlotValue("blue", 1.0, 1)
    ranked = [(catalog.asins[0], 1.0)]
    assert choose_ask_attribute(catalog, state, ranked, config) is None


def test_blue_shirt_does_not_ask_category(records):
    agent = Agent(
        catalog=records,
        config=Config(lexical_enabled=False, dense_enabled=False, exact_phrase_enabled=True),
    )
    agent.reset("s1", {})
    out = agent.respond("s1", "blue shirt", turn=1, top_k=10)
    assert out["ask_attribute"] != "category"


def test_does_not_ask_category_for_shirt_only(records):
    agent = Agent(
        catalog=records,
        config=Config(lexical_enabled=False, dense_enabled=False, exact_phrase_enabled=True),
    )
    agent.reset("s1", {})
    out = agent.respond("s1", "shirt", turn=1, top_k=10)
    assert out["ask_attribute"] != "category"


def test_confused_reply_is_decline_but_questions_are_not(catalog, config):
    extractor = ConstraintExtractor(catalog, config)
    assert extractor.utterance_is_decline("?")
    assert extractor.utterance_is_decline("huh")
    assert extractor.utterance_is_decline("what")
    assert extractor.utterance_is_decline("I don't know")
    assert extractor.utterance_is_decline("whatever you think")
    assert not extractor.utterance_is_decline("what size")
    assert not extractor.utterance_is_decline("blue shirt")
