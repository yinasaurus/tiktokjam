"""R9 / TDD §6.4 — no cross-session leakage."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config


def test_reset_isolates_sessions(records):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("buy", {"name": "a"})
    agent.respond("buy", "navy cotton crew neck t-shirt", turn=1, top_k=5)

    agent.reset("browse", {"name": "b"})
    state_b = agent._sessions["browse"]
    assert state_b.slots == {}
    assert state_b.asked == []
    assert state_b.last_candidates == []
    assert state_b.user_profile == {"name": "b"}

    state_a = agent._sessions["buy"]
    assert state_a.slots or state_a.free_constraints or state_a.leaf_category


def test_two_sessions_do_not_share_asked(records):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("s1", {})
    agent.reset("s2", {})
    agent.respond("s1", "cotton t-shirts", turn=1, top_k=5)
    agent._sessions["s1"].mark_asked("color")
    assert "color" not in agent._sessions["s2"].asked
