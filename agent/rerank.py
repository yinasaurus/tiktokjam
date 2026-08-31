"""Reranker cascade (TDD §9). M1 ships a linear heuristic; M3 swaps in LightGBM."""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from agent.config import Config
from agent.determinism import stable_order
from agent.rank_features import feature_vector, heuristic_score
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
    if config.rerank_mode in {"ltr", "cascade"}:
        # Submitted FastAgent does not call this module. Hybrid LTR needs
        # models/ltr.txt; if that file is missing, fall through to heuristic.
        ltr_ranked = ltr_rerank(ranked, catalog, state, constraints, config)
        if ltr_ranked is not None:
            return ltr_ranked
    return heuristic_rerank(ranked, catalog, state, constraints)


def heuristic_rerank(
    ranked: list[tuple[str, float]],
    catalog: CatalogStore,
    state: SessionState,
    constraints: list[Constraint],
) -> list[tuple[str, float]]:
    """Cheap linear combination of the TDD §9.2 features. No trained model."""
    scored: list[tuple[float, str]] = []
    for asin, rrf in ranked:
        score = heuristic_score(asin, rrf, catalog, state, constraints)
        scored.append((score, asin))
    order = stable_order(scored)
    return [(scored[i][1], scored[i][0]) for i in order]


def ltr_rerank(
    ranked: list[tuple[str, float]],
    catalog: CatalogStore,
    state: SessionState,
    constraints: list[Constraint],
    config: Config,
) -> list[tuple[str, float]] | None:
    booster = _load_ltr(config.ltr_model_path)
    if booster is None:
        return None
    matrix = [feature_vector(asin, score, catalog, state, constraints, config) for asin, score in ranked]
    try:
        predictions = booster.predict(matrix)
    except Exception:
        return None
    scored = [(float(predictions[i]), ranked[i][0]) for i in range(len(ranked))]
    order = stable_order(scored)
    return [(scored[i][1], scored[i][0]) for i in order]


@lru_cache(maxsize=4)
def _load_ltr(path_raw: str):
    path = Path(path_raw)
    if not path.exists():
        return None
    try:
        import lightgbm as lgb

        return lgb.Booster(model_file=str(path))
    except Exception:
        return None
