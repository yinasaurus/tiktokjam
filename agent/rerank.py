"""Reranker cascade (TDD §9). M1 ships a linear heuristic; M3 swaps in LightGBM."""

from __future__ import annotations

import math

from agent.lexicon import canonical_gender, expand_terms
from agent.config import Config
from agent.determinism import stable_order
from agent.state import SessionState
from agent.types import Constraint


def fused_margin(ranked: list[tuple[str, float]]) -> float:
    if len(ranked) < 2:
        return 1.0
    s0, s1 = ranked[0][1], ranked[1][1]
    return (s0 - s1) / max(s0, 1e-9)


def rerank(
    ranked: list[tuple[str, float]],
    catalog: CatalogStore,
    state: SessionState,
    constraints: list[Constraint],
    config: Config,
) -> list[tuple[str, float]]:
    if config.rerank_mode == "off" or len(ranked) <= 1:
        return ranked
    margin = fused_margin(ranked)
    if config.rerank_mode == "cascade" and margin > config.margin_tau_high:
        return ranked
    return heuristic_rerank(ranked, catalog, state, constraints)


def heuristic_rerank(
    ranked: list[tuple[str, float]],
    catalog: CatalogStore,
    state: SessionState,
    constraints: list[Constraint],
) -> list[tuple[str, float]]:
    """Cheap linear combination of the TDD §9.2 features. No trained model."""
    phrases = [c.text for c in constraints if c.text]
    leaf = (state.leaf_category or "").lower()
    session_tokens: set[str] = set()
    for phrase in phrases:
        session_tokens.update(expand_terms(phrase))
    if leaf:
        session_tokens.update(expand_terms(leaf))
    session_tokens.update(expand_terms(state.last_utterance or ""))
    want_gender = None
    for key in ("department", "style"):
        slot = state.slots.get(key)
        if slot:
            want_gender = canonical_gender(slot.value) or want_gender
    scored: list[tuple[float, str]] = []
    rrf_by_asin = {asin: rrf for asin, rrf in ranked}
    has_constraints = bool(phrases or leaf)
    pop_weight = 0.005 if has_constraints else 0.04
    for asin, rrf in ranked:
        product = catalog.get(asin)
        if product is None:
            scored.append((rrf, asin))
            continue
        coverage = 0.0
        conf_sum = 0.0
        conf_n = 0
        blob = product.text_blob
        attrs = product.attr_phrases
        for i, phrase in enumerate(phrases):
            hit = phrase in attrs or phrase in blob
            if hit:
                coverage += 1.0
                conf_sum += constraints[i].confidence if i < len(constraints) else 1.0
                conf_n += 1
        denom = max(len(phrases), 1)
        coverage_ratio = coverage / denom
        mean_conf = (conf_sum / conf_n) if conf_n else 0.0
        cat_exact = 1.0 if product.leaf_category.lower() == leaf and leaf else 0.0
        path_overlap = 0.0
        if leaf:
            path_overlap = sum(
                1.0 for c in product.category_path if leaf in c.lower() or c.lower() in leaf
            )
        title_overlap = 0.0
        if session_tokens:
            title_toks = set(expand_terms(product.title.lower()))
            title_overlap = len(session_tokens & title_toks) / max(len(session_tokens), 1)
        pop = math.log1p(product.rating_count)
        sparse_pen = 0.15 if product.is_sparse else 0.0
        unmatched_pen = 1.5 if has_constraints and coverage_ratio == 0.0 and cat_exact == 0.0 else 0.0
        gender_boost = 0.0
        gender_pen = 0.0
        if want_gender:
            if product.department == want_gender:
                gender_boost = 1.8
            elif product.department:
                gender_pen = 4.0
        score = (
            rrf_by_asin[asin]
            + 2.0 * coverage_ratio
            + 0.6 * mean_conf
            + 0.8 * cat_exact
            + 0.15 * path_overlap
            + 0.4 * title_overlap
            + pop_weight * pop
            + gender_boost
            - sparse_pen
            - unmatched_pen
            - gender_pen
        )
        scored.append((score, asin))
    order = stable_order(scored)
    return [(scored[i][1], scored[i][0]) for i in order]
