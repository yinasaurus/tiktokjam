"""bm25s lexical route (TDD §7.2). Optional: degrades to empty if bm25s is missing."""

from __future__ import annotations

from agent.catalog import CatalogStore
from agent.config import Config
from agent.determinism import pin_runtime
from agent.types import Constraint

pin_runtime()


class LexicalIndex:
    def __init__(self, catalog: CatalogStore, config: Config) -> None:
        self.catalog = catalog
        self.config = config
        self._retriever = None
        self.available = False
        if not config.lexical_enabled:
            return
        try:
            import bm25s
        except ImportError:
            return
        corpus = [p.text_blob for p in catalog.products]
        tokens = bm25s.tokenize(corpus, stopwords="en", show_progress=False)
        retriever = bm25s.BM25()
        retriever.index(tokens, show_progress=False)
        self._bm25s = bm25s
        self._retriever = retriever
        self.available = True

    def retrieve(
        self,
        constraints: list[Constraint],
        utterance: str,
        k: int,
    ) -> list[tuple[str, float]]:
        if not self.available or self._retriever is None or k <= 0:
            return []
        parts = [c.text for c in constraints if c.text]
        if utterance:
            parts.append(utterance)
        query = " ".join(parts).strip()
        if not query:
            return []
        try:
            q_tokens = self._bm25s.tokenize([query], stopwords="en", show_progress=False)
            docs, scores = self._retriever.retrieve(q_tokens, k=min(k, len(self.catalog)))
            # docs/scores are shape (1, k)
            doc_row = docs[0]
            score_row = scores[0]
            pairs = [
                (self.catalog.asins[int(d)], float(s))
                for d, s in zip(doc_row, score_row)
                if int(d) >= 0 and float(s) > 0.0
            ]
            # Stable tie-break on asin.
            pairs.sort(key=lambda p: (-p[1], p[0]))
            return pairs[:k]
        except Exception:
            return []
