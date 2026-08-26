"""Process-level determinism. Import this module before numpy.

Pinning BLAS threads to 1 is required: non-associative float reduction
changes rank order across thread counts (NFR-10, TDD §12.1).
"""

from __future__ import annotations

import os
from collections.abc import Sequence

# Thread pins MUST happen before numpy/scipy/OpenBLAS initialise.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("PYTHONHASHSEED", "0")

# Offline HuggingFace / transformers. setdefault so a vendor script can
# export HF_HUB_OFFLINE=0 for a one-time model download (NFR-12).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")


def pin_runtime() -> None:
    """Idempotent; safe to call from other modules as a belt-and-braces import."""
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    os.environ.setdefault("PYTHONHASHSEED", "0")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")


def ranked_indices(scores, asin_codes):
    """Return indices sorted best-first by (-score, asin_code).

    Uses a full lexsort. At 50k this is a few milliseconds and, unlike
    argpartition, is deterministic on the k-boundary when scores tie
    (NFR-11, TDD §12.2).
    """
    import numpy as np

    scores = np.asarray(scores)
    asin_codes = np.asarray(asin_codes)
    return np.lexsort((asin_codes, -scores))


def topk_indices(scores, asin_codes, k: int):
    """Deterministic top-k indices, best first."""
    import numpy as np

    scores = np.asarray(scores)
    asin_codes = np.asarray(asin_codes)
    n = int(scores.shape[0])
    k = int(min(max(k, 0), n))
    if k == 0:
        return np.empty(0, dtype=np.int64)
    order = ranked_indices(scores, asin_codes)
    return order[:k]


def stable_order(pairs: Sequence[tuple[float, str]]) -> list[int]:
    """Return indices of (score, asin) pairs sorted by (-score, asin)."""
    return sorted(range(len(pairs)), key=lambda i: (-pairs[i][0], pairs[i][1]))
