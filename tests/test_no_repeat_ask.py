"""FR-19 — never re-ask an attribute already asked or declined."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config


def test_no_repeat_ask_within_session(records):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("s1", {})
    asked: list[str] = []
    utterances = [
        "looking for clothes",
        "something casual",
        "I don't know",
        "maybe cotton",
        "navy is fine",
        "regular fit",
        "not sure",
        "whatever you think",
        "still looking",
        "show me more",
    ]
    for turn, msg in enumerate(utterances, start=1):
        out = agent.respond("s1", msg, turn=turn, top_k=10)
        attr = out["ask_attribute"]
        if attr is not None:
            if attr != "other":
                assert attr not in asked, f"repeated ask_attribute={attr!r} at turn {turn}"
            asked.append(attr)
    non_other = [attr for attr in asked if attr != "other"]
    assert len(non_other) == len(set(non_other))
    assert asked.count("other") <= Config().other_ask_max
