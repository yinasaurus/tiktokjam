"""Exact-phrase inverted index (TDD §7.1). Counting, not intersection."""

from __future__ import annotations

from agent.catalog import CatalogStore
from agent.config import Config
from agent.determinism import pin_runtime, ranked_indices
from agent.normalise import normalise
from agent.types import Constraint

pin_runtime()


class ExactPhraseIndex:
    def __init__(self, catalog: CatalogStore, config: Config) -> None:
        self.catalog = catalog
        self.config = config

    def retrieve(self, constraints: list[Constraint], k: int) -> list[tuple[str, float]]:
        if not self.config.exact_phrase_enabled or k <= 0:
            return []
        n = len(self.catalog.products)
        if n == 0:
            return []

        import numpy as np

        scores = np.zeros(n, dtype=np.float32)
        matched_any = False
        for constraint in constraints:
            docs = self.catalog.phrase_to_docs.get(constraint.text)
            if not docs:
                continue
            matched_any = True
            idf = self.catalog.phrase_idf.get(constraint.text, 1.0)
            weight = max(0.0, float(constraint.confidence)) * idf
            for doc_id in docs:
                scores[doc_id] += weight

        leaf = next(
            (c.text for c in constraints if c.source == "category" and c.text),
            None,
        )
        if leaf:
            boost = self.config.leaf_category_boost
            for i, product in enumerate(self.catalog.products):
                if normalise(product.leaf_category) == leaf:
                    scores[i] += boost

        if not matched_any and leaf is None:
            return []

        asin_codes = np.asarray(self.catalog.asin_codes, dtype=np.int32)
        order = ranked_indices(scores, asin_codes)
        out: list[tuple[str, float]] = []
        for idx in order:
            s = float(scores[int(idx)])
            if s <= 0.0:
                break
            out.append((self.catalog.asins[int(idx)], s))
            if len(out) >= k:
                break
        return out
