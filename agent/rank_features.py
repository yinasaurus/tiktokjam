"""Shared reranking features for heuristic and LightGBM paths."""

from __future__ import annotations

import math

from agent.catalog import CatalogStore
from agent.config import Config
from agent.lexicon import canonical_gender, expand_terms
from agent.state import SessionState
from agent.types import Constraint

FEATURE_NAMES: tuple[str, ...] = (
    "fused_score",
    "coverage_ratio",
    "mean_confidence",
    "leaf_category_exact",
    "category_path_overlap",
    "title_token_overlap",
    "log_rating_count",
    "is_sparse",
    "gender_match",
    "gender_mismatch",
    "unmatched_constraints",
    "price_present",
    "avg_rating",
)


def session_terms(state: SessionState, constraints: list[Constraint]) -> set[str]:
    terms: set[str] = set()
    for constraint in constraints:
        if constraint.text:
            terms.update(expand_terms(constraint.text))
    if state.leaf_category:
        terms.update(expand_terms(state.leaf_category))
    if state.last_utterance:
        terms.update(expand_terms(state.last_utterance))
    return terms


def wanted_gender(state: SessionState) -> str | None:
    want = None
    for key in ("department", "style"):
        slot = state.slots.get(key)
        if slot:
            want = canonical_gender(slot.value) or want
    return want


def feature_vector(
    asin: str,
    fused_score: float,
    catalog: CatalogStore,
    state: SessionState,
    constraints: list[Constraint],
    config: Config | None = None,
) -> list[float]:
    product = catalog.get(asin)
    if product is None:
        return [float(fused_score)] + [0.0] * (len(FEATURE_NAMES) - 1)

    phrases = [c.text for c in constraints if c.text]
    leaf = (state.leaf_category or "").lower()
    blob = product.text_blob
    attrs = product.attr_phrases

    coverage = 0.0
    conf_sum = 0.0
    conf_n = 0
    for i, phrase in enumerate(phrases):
        hit = phrase in attrs or phrase in blob
        if hit:
            coverage += 1.0
            conf_sum += constraints[i].confidence if i < len(constraints) else 1.0
            conf_n += 1

    has_constraints = bool(phrases or leaf)
    coverage_ratio = coverage / max(len(phrases), 1)
    mean_conf = (conf_sum / conf_n) if conf_n else 0.0
    cat_exact = 1.0 if product.leaf_category.lower() == leaf and leaf else 0.0
    path_overlap = 0.0
    if leaf:
        path_overlap = sum(
            1.0 for c in product.category_path if leaf in c.lower() or c.lower() in leaf
        )

    title_overlap = 0.0
    terms = session_terms(state, constraints)
    if terms:
        title_toks = set(expand_terms(product.title.lower()))
        title_overlap = len(terms & title_toks) / max(len(terms), 1)

    want_gender = wanted_gender(state)
    gender_match = 0.0
    gender_mismatch = 0.0
    if want_gender:
        if product.department == want_gender:
            gender_match = 1.0
        elif product.department:
            gender_mismatch = 1.0

    unmatched = 1.0 if has_constraints and coverage_ratio == 0.0 and cat_exact == 0.0 else 0.0

    return [
        float(fused_score),
        float(coverage_ratio),
        float(mean_conf),
        float(cat_exact),
        float(path_overlap),
        float(title_overlap),
        float(math.log1p(product.rating_count)),
        1.0 if product.is_sparse else 0.0,
        gender_match,
        gender_mismatch,
        unmatched,
        1.0 if product.price is not None else 0.0,
        float(product.avg_rating),
    ]


def heuristic_score(
    asin: str,
    fused_score: float,
    catalog: CatalogStore,
    state: SessionState,
    constraints: list[Constraint],
) -> float:
    product = catalog.get(asin)
    features = dict(zip(FEATURE_NAMES, feature_vector(asin, fused_score, catalog, state, constraints)))
    has_constraints = bool([c.text for c in constraints if c.text] or state.leaf_category)
    pop_weight = 0.005 if has_constraints else 0.04
    return (
        features["fused_score"]
        + 2.0 * features["coverage_ratio"]
        + 0.6 * features["mean_confidence"]
        + 0.8 * features["leaf_category_exact"]
        + 0.15 * features["category_path_overlap"]
        + 0.4 * features["title_token_overlap"]
        + pop_weight * features["log_rating_count"]
        + 1.8 * features["gender_match"]
        - 0.15 * features["is_sparse"]
        - 1.5 * features["unmatched_constraints"]
        - 4.0 * features["gender_mismatch"]
    ) if product is not None else float(fused_score)
