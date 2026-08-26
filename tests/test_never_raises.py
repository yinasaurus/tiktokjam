"""FR-5 — each stage may raise; respond() still returns a valid payload."""

from __future__ import annotations

from agent.agent import Agent
from agent.config import Config
from agent.extract import ConstraintExtractor
from agent.routes.exact_phrase import ExactPhraseIndex


def _valid(out, catalog, top_k=10):
    assert isinstance(out, dict)
    recs = out["recommendations"]
    assert len(recs) == min(top_k, len(catalog))
    assert len(recs) == len(set(recs))
    assert all(a in catalog.asin_to_idx for a in recs)
    assert out["ask_attribute"] is None or out["ask_attribute"] in Config().ask_attributes
    assert out["usage"]["total_tokens"] >= 0


def test_extract_raises(monkeypatch, records, catalog):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("s1", {})

    def boom(*_a, **_k):
        raise RuntimeError("extract failed")

    monkeypatch.setattr(ConstraintExtractor, "extract", boom)
    out = agent.respond("s1", "cotton crew neck", turn=1, top_k=10)
    _valid(out, catalog)


def test_exact_phrase_raises(monkeypatch, records, catalog):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("s1", {})

    def boom(*_a, **_k):
        raise RuntimeError("route failed")

    monkeypatch.setattr(ExactPhraseIndex, "retrieve", boom)
    out = agent.respond("s1", "cotton crew neck", turn=1, top_k=10)
    _valid(out, catalog)


def test_fusion_raises(monkeypatch, records, catalog):
    agent = Agent(catalog=records, config=Config(lexical_enabled=False, dense_enabled=False))
    agent.reset("s1", {})

    def boom(*_a, **_k):
        raise RuntimeError("fusion failed")

    monkeypatch.setattr("agent.agent.fuse", boom)
    out = agent.respond("s1", "cotton crew neck", turn=1, top_k=10)
    _valid(out, catalog)
