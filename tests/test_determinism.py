"""NFR-9 — two fresh agents, identical inputs, identical recommendations."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config


def test_two_agents_byte_identical_recs(records):
    cfg = Config(lexical_enabled=False, dense_enabled=True, exact_phrase_enabled=True)
    messages = [
        (1, "looking for navy cotton t-shirts"),
        (2, "crew neck please"),
    ]

    def run():
        agent = Agent(catalog=records, config=cfg)
        agent.reset("s1", {"age": 30})
        outs = []
        for turn, msg in messages:
            outs.append(agent.respond("s1", msg, turn=turn, top_k=10))
        return outs

    a, b = run(), run()
    for oa, ob in zip(a, b):
        assert oa["recommendations"] == ob["recommendations"]
        assert oa["ask_attribute"] == ob["ask_attribute"]
        assert oa["usage"] == ob["usage"]


def test_stable_sort_tie_break(catalog):
    from agent.determinism import ranked_indices
    import numpy as np

    scores = np.array([1.0, 1.0, 0.5], dtype=np.float32)
    codes = np.array(catalog.asin_codes[:3], dtype=np.int32)
    order = ranked_indices(scores, codes)
    # Equal top scores must be ordered by asin_code (lexicographic asin).
    first, second = int(order[0]), int(order[1])
    assert scores[first] == scores[second]
    assert codes[first] <= codes[second]
