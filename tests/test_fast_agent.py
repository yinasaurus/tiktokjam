from __future__ import annotations

from agent.fast_agent import Agent
from agent.types import asins_of
from tests.conftest import FIXTURE_PATH


def test_fast_agent_repairs_semicolon_fragmented_constraints():
    agent = Agent(FIXTURE_PATH)
    agent.by_constraint["Care: wipe clean; imported"].add("B000000001")

    repaired = agent._repair_constraints(("Care: wipe clean", "imported", "cotton"))

    assert repaired == ["Care: wipe clean; imported", "cotton"]


def test_fast_agent_waits_for_enough_evidence_before_emitting_recommendations():
    agent = Agent(FIXTURE_PATH)
    agent.reset("session", {})

    first = agent.respond(
        "session",
        "I'm looking for Men T-Shirts, but I'm still exploring.",
        turn=1,
        top_k=10,
    )
    assert asins_of(first) == []
    assert first["ask_attribute"] == "other"

    second = agent.respond(
        "session",
        "For that, what matters is: cotton; 100% cotton.",
        turn=2,
        top_k=10,
    )
    assert len(asins_of(second)) == 10
