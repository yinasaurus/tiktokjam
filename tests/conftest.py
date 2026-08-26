from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.catalog import CatalogStore
from agent.config import Config

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "catalog.jsonl"


@pytest.fixture
def records() -> list[dict]:
    rows = []
    with FIXTURE_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


@pytest.fixture
def catalog(records) -> CatalogStore:
    return CatalogStore.from_records(records, sparse_threshold=2)


@pytest.fixture
def config() -> Config:
    return Config(
        lexical_enabled=False,  # unit tests must not require bm25s
        dense_enabled=True,
        exact_phrase_enabled=True,
        K_exact=12,
        K_dense=12,
        N_fuse=12,
        min_information_gain=0.01,
    )
