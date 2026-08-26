"""Dense brute-force route (TDD §7.3). Exact matmul, no ANN (NG-8)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agent.catalog import CatalogStore
from agent.config import Config
from agent.determinism import pin_runtime, topk_indices
from agent.types import Constraint

pin_runtime()


class Encoder:
    dim: int

    def encode(self, texts: Sequence[str]):
        raise NotImplementedError


class HashEncoder:
    """Deterministic bag-of-tokens encoder for tests and encoder-less smoke runs.

    Not a production retriever. Production uses Model2Vec loaded from a local
    path (TDD §4.3 / §13.2).
    """

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def encode(self, texts: Sequence[str]):
        import numpy as np

        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in str(text).lower().split():
                digest = hashlib.sha256(tok.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dim
                bump = 1.0 + (int.from_bytes(digest[4:8], "little") % 7) * 0.1
                out[i, idx] += bump
            norm = float(np.linalg.norm(out[i]))
            if norm > 0.0:
                out[i] /= norm
        return out


class Model2VecEncoder:
    def __init__(self, model_dir: str | Path) -> None:
        from model2vec import StaticModel

        path = Path(model_dir)
        if not path.exists():
            raise FileNotFoundError(f"encoder directory not found: {path}")
        self._model = StaticModel.from_pretrained(str(path))
        probe = self._model.encode(["probe"])
        self.dim = int(probe.shape[-1])

    def encode(self, texts: Sequence[str]):
        import numpy as np

        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(list(texts))
        arr = np.asarray(vecs, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return arr / norms


@dataclass
class PhraseEmbeddingTable:
    phrases: tuple[str, ...]
    matrix: object  # np.ndarray (P, D), L2-normalised
    codes: object  # np.ndarray (P,) int32


class DenseIndex:
    def __init__(
        self,
        catalog: CatalogStore,
        config: Config,
        encoder: Encoder | None = None,
        embeddings=None,
    ) -> None:
        self.catalog = catalog
        self.config = config
        self.encoder = encoder
        self.available = False
        self.embeddings = None
        self.phrase_table: PhraseEmbeddingTable | None = None
        if not config.dense_enabled or encoder is None:
            return
        import numpy as np

        if embeddings is None:
            blobs = [p.text_blob or p.title for p in catalog.products]
            embeddings = encoder.encode(blobs)
        mat = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        self.embeddings = mat / norms
        self.available = True

        phrases = tuple(sorted(catalog.phrase_vocab))
        if phrases:
            pmat = encoder.encode(list(phrases))
            pmat = np.asarray(pmat, dtype=np.float32)
            pn = np.linalg.norm(pmat, axis=1, keepdims=True)
            pn = np.maximum(pn, 1e-12)
            self.phrase_table = PhraseEmbeddingTable(
                phrases=phrases,
                matrix=pmat / pn,
                codes=np.arange(len(phrases), dtype=np.int32),
            )

    def retrieve(
        self,
        constraints: list[Constraint],
        utterance: str,
        leaf_category: str | None,
        k: int,
        cached_vec=None,
    ) -> tuple[list[tuple[str, float]], object]:
        if not self.available or self.embeddings is None or self.encoder is None or k <= 0:
            return [], cached_vec
        import numpy as np

        query = _build_query(leaf_category, constraints, utterance)
        if not query:
            return [], cached_vec
        if cached_vec is not None:
            q = np.asarray(cached_vec, dtype=np.float32)
        else:
            q = self.encoder.encode([query])[0]
            nrm = float(np.linalg.norm(q))
            if nrm > 0.0:
                q = q / nrm
        scores = self.embeddings @ q
        asin_codes = np.asarray(self.catalog.asin_codes, dtype=np.int32)
        order = topk_indices(scores, asin_codes, k)
        pairs = [(self.catalog.asins[int(i)], float(scores[int(i)])) for i in order]
        return pairs, q


def _build_query(
    leaf_category: str | None,
    constraints: list[Constraint],
    utterance: str,
) -> str:
    parts: list[str] = []
    if leaf_category:
        parts.append(leaf_category)
    texts = [c.text for c in constraints if c.text]
    if texts:
        parts.append(" ".join(texts))
    if utterance:
        parts.append(utterance)
    return ". ".join(parts)


def load_encoder(config: Config) -> Encoder | None:
    path = Path(config.encoder_dir)
    if path.exists() and any(path.iterdir()):
        try:
            return Model2VecEncoder(path)
        except Exception:
            return None
    return None
