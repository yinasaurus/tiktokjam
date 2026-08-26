"""FR-8 / FR-17 — partial override keeps unrelated slots."""

from __future__ import annotations

from agent.config import Config
from agent.state import DialogStateManager, SessionState
from agent.types import Constraint


def test_partial_override_retains_other_slots():
    mgr = DialogStateManager(Config(retain_superseded=True))
    state = SessionState(session_id="s", user_profile={})
    mgr.apply(
        state,
        [
            Constraint("navy", "color", 1.0, "exact", 1),
            Constraint("cotton", "material", 1.0, "exact", 1),
        ],
        turn=1,
    )
    mgr.apply(
        state,
        [Constraint("black", "color", 1.0, "exact", 2)],
        turn=2,
    )
    assert state.slots["color"].value == "black"
    assert "navy" in state.slots["color"].superseded
    assert state.slots["material"].value == "cotton"


def test_category_change_clears_slots_but_keeps_superseded():
    mgr = DialogStateManager(Config(retain_superseded=True))
    state = SessionState(session_id="s", user_profile={})
    mgr.apply(
        state,
        [
            Constraint("t-shirts", "category", 1.0, "category", 1),
            Constraint("navy", "color", 1.0, "exact", 1),
        ],
        turn=1,
    )
    mgr.apply(
        state,
        [Constraint("jeans", "category", 1.0, "category", 3)],
        turn=3,
    )
    assert state.leaf_category == "jeans"
    assert state.slots == {}
