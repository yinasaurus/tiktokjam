"""Question policy — entropy + stopping rule (TDD §10). Biased toward not asking."""

from __future__ import annotations

import math
from collections import Counter

from agent.catalog import CatalogStore, Product
from agent.config import Config
from agent.state import SessionState

# Maps official ask_attribute values to product.details keys (lowercased).
_ATTR_KEYS: dict[str, tuple[str, ...]] = {
    "color": ("color", "colour", "color name"),
    "size": ("size", "sizes"),
    "brand": ("brand", "manufacturer", "publisher", "store"),
    "material": ("material", "fabric", "fabric type"),
    "style": ("style", "department", "fit", "fit type"),
    "feature": ("feature", "pattern", "print"),
    "use_case": ("occasion", "sport", "use"),
}


def choose_ask_attribute(
    catalog: CatalogStore,
    state: SessionState,
    ranked: list[tuple[str, float]],
    config: Config,
) -> str | None:
    if (
        config.question_strategy == "simulator_other"
        and len(ranked) >= 2
        and "other" in config.ask_attributes
        and state.asked.count("other") < config.other_ask_max
    ):
        return "other"

    filled = set(state.slots.keys())
    if state.leaf_category:
        filled.add("category")

    available = [
        a
        for a in config.ask_attributes
        if a not in state.asked_set()
        and a not in state.declined_set()
        and a not in filled
        and a not in {"other", "category", "brand"}
    ]
    if not available:
        return None

    # Already know the product type and at least one preference — don't grill.
    if state.leaf_category and state.slots:
        return None

    candidates = [catalog.get(asin) for asin, _ in ranked[: max(config.N_fuse, 10)]]
    products = [p for p in candidates if p is not None]
    if not products:
        return None

    entropy = _pool_entropy(ranked[: len(products)])
    if entropy < math.log(max(config.entropy_stop_s_target, 1)):
        return None

    best_attr: str | None = None
    best_gain = 0.0
    for attr in available:
        gain = _expected_gain(products, attr, entropy)
        if gain > best_gain:
            best_gain = gain
            best_attr = attr

    if best_attr is None or best_gain < config.min_information_gain:
        return None
    return best_attr


def _pool_entropy(ranked: list[tuple[str, float]]) -> float:
    if not ranked:
        return 0.0
    scores = [max(s, 0.0) for _, s in ranked]
    total = sum(scores)
    if total <= 0.0:
        n = len(ranked)
        return math.log(n) if n > 1 else 0.0
    h = 0.0
    for s in scores:
        p = s / total
        if p > 0.0:
            h -= p * math.log(p)
    return h


def _values_for(product: Product, attr: str) -> list[str]:
    if attr == "budget":
        if product.price is None:
            return []
        if product.price < 20:
            return ["low"]
        if product.price < 50:
            return ["mid"]
        return ["high"]
    if attr == "category":
        return [product.leaf_category.lower()] if product.leaf_category else []
    keys = _ATTR_KEYS.get(attr, (attr,))
    out: list[str] = []
    for key in keys:
        val = product.details.get(key)
        if val:
            out.append(val.lower())
    return out


def _expected_gain(products: list[Product], attr: str, entropy_before: float) -> float:
    values: list[str] = []
    for p in products:
        vs = _values_for(p, attr)
        if vs:
            values.append(vs[0])
    if len(values) < 2:
        return 0.0
    counts = Counter(values)
    n = sum(counts.values())
    if n < 2:
        return 0.0
    remaining = 0.0
    for c in counts.values():
        p = c / n
        # Approximate H(C | a=v) as log of bucket size.
        bucket_h = math.log(c) if c > 1 else 0.0
        remaining += p * bucket_h
    return max(0.0, entropy_before - remaining)
