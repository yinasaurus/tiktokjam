"""Weighted RRF fusion with skip-missing, agreement boost, empty-pool recovery."""

from __future__ import annotations

from agent.catalog import CatalogStore
from agent.config import Config
from agent.determinism import stable_order


def fuse(
    route_hits: dict[str, list[tuple[str, float]]],
    config: Config,
    n_fuse: int | None = None,
) -> list[tuple[str, float]]:
    """Skip-missing weighted RRF + agreement boost (TDD §8).

    A document absent from a route contributes nothing — we do not
    substitute rank = len+1.
    """
    gated: dict[str, list[tuple[str, float]]] = {}
    floors = config.route_confidence_floor
    for name, hits in route_hits.items():
        if not hits:
            continue
        floor = float(floors.get(name, 0.0))
        if hits[0][1] < floor:
            continue
        gated[name] = hits

    scores: dict[str, float] = {}
    containing: dict[str, int] = {}
    for name, hits in gated.items():
        weight = config.route_weight(name)
        for rank, (asin, _raw) in enumerate(hits, start=1):
            scores[asin] = scores.get(asin, 0.0) + weight / (config.rrf_k + rank)
            containing[asin] = containing.get(asin, 0) + 1

    alpha = config.agreement_alpha
    boosted: list[tuple[float, str]] = []
    for asin, score in scores.items():
        n = containing[asin]
        boosted.append((score * (1.0 + alpha * (n - 1)), asin))

    order = stable_order(boosted)
    limit = n_fuse if n_fuse is not None else config.N_fuse
    out: list[tuple[str, float]] = []
    for i in order[:limit]:
        score, asin = boosted[i]
        out.append((asin, score))
    return out


def backfill_popularity(
    ranked: list[tuple[str, float]],
    catalog: CatalogStore,
    top_k: int,
) -> list[tuple[str, float]]:
    """Guarantee min(top_k, |catalog|) unique catalog-resident ASINs (FR-2, FR-23)."""
    seen: set[str] = set()
    out: list[tuple[str, float]] = []
    for asin, score in ranked:
        if asin in seen:
            continue
        if asin not in catalog.asin_to_idx:
            continue
        seen.add(asin)
        out.append((asin, score))
        if len(out) >= top_k:
            return out
    for asin in catalog.popularity_asins():
        if asin in seen:
            continue
        seen.add(asin)
        out.append((asin, 0.0))
        if len(out) >= top_k:
            break
    return out
