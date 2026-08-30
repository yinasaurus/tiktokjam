"""Build (or rebuild) in-memory indices and optionally cache dense embeddings.

Usage:
    python scripts/build_index.py --catalog path/to/catalog.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.catalog import CatalogStore
from agent.config import Config
from agent.routes.dense import DenseIndex, load_encoder


def _catalog_key(path: Path, config: Config) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    digest.update(config.model_id.encode("utf-8"))
    digest.update(str(config.sparse_threshold).encode("utf-8"))
    return digest.hexdigest()[:16]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("cache"))
    args = parser.parse_args()

    config = Config(cache_dir=str(args.cache_dir))
    t0 = time.perf_counter()
    print(f"loading catalog: {args.catalog}", flush=True)
    store = CatalogStore.load_cached(
        args.catalog,
        sparse_threshold=config.sparse_threshold,
        cache_dir=args.cache_dir,
    )
    print(f"catalog: {len(store)} products in {time.perf_counter() - t0:.2f}s")
    print(f"phrase vocab: {len(store.phrase_vocab)}")
    print(f"sparse listings: {sum(1 for p in store.products if p.is_sparse)}")

    print(f"loading encoder from {config.encoder_dir}", flush=True)
    encoder = load_encoder(config)
    if encoder is None:
        print("no vendored encoder at", config.encoder_dir, "— skipping dense cache")
        return

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    key = _catalog_key(args.catalog, config)
    npz_path = args.cache_dir / f"{key}.npz"
    t1 = time.perf_counter()
    print("building dense index", flush=True)
    index = DenseIndex(store, config, encoder=encoder)
    print(f"dense index: available={index.available} in {time.perf_counter() - t1:.2f}s")
    if index.available:
        import numpy as np

        tmp = npz_path.with_suffix(".tmp.npz")
        np.savez(tmp, embeddings=index.embeddings)
        tmp.replace(npz_path)
        print("wrote", npz_path)


if __name__ == "__main__":
    main()
