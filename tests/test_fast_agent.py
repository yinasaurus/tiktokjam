from __future__ import annotations

from agent.fast_agent import Agent
from tests.conftest import FIXTURE_PATH


def test_fast_agent_repairs_semicolon_fragmented_constraints():
    agent = Agent(FIXTURE_PATH)
    agent.by_constraint["Care: wipe clean; imported"].add("B000000001")

    repaired = agent._repair_constraints(("Care: wipe clean", "imported", "cotton"))

    assert repaired == ["Care: wipe clean; imported", "cotton"]
