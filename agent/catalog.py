"""Catalog normalisation and defensive field parsing (FR-21, TDD §3)."""

from __future__ import annotations

import gzip
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.determinism import pin_runtime
from agent.normalise import HEADER_STOPLIST, is_indexable_phrase, ngrams, normalise, strip_html

pin_runtime()

_PRICE_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")
_MISSING_STRINGS = frozenset({"none", "nan", "null", "n/a", "na", "nil", ""})


def parse_price(value: Any) -> float | None:
    """Never call float() on the raw field.

    The Amazon 2023 clothing slice ships `price` as a string, with missing
    encoded as the literal `"None"` (PRD §6.6.8). Ranges take the low end.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    s = str(value).strip()
    if s.lower() in _MISSING_STRINGS:
        return None
    compact = s.replace(",", "")
    match = _PRICE_NUMBER_RE.search(compact)
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_details(value: Any) -> dict[str, str]:
    """`details` may be a dict, a JSON string, or missing. Always return a dict."""
    raw: Any = value
    if raw is None or raw == "":
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, str] = {}
    # Sort keys so downstream iteration is deterministic (NFR-11).
    for key in sorted(raw.keys(), key=lambda k: str(k).lower()):
        k = str(key).strip().lower()
        if not k:
            continue
        v = raw[key]
        if v is None:
            continue
        text = str(v).strip()
        if not text or text.lower() in _MISSING_STRINGS:
            continue
        out[k] = text
    return out


def parse_string_list(value: Any) -> list[str]:
    """Coerce features / description / categories to a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        items: Iterable[Any] = [value]
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        items = [value]
    out: list[str] = []
    for item in items:
        if item is None:
            continue
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def clean_description(value: Any) -> str:
    parts = parse_string_list(value)
    kept: list[str] = []
    for part in parts:
        text = strip_html(part)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if text.lower().strip(" :") in HEADER_STOPLIST:
            continue
        kept.append(text)
    return " ".join(kept)


def parse_rating(value: Any, default: float = 0.0) -> float:
    if value is None or value == "" or str(value).strip().lower() in _MISSING_STRINGS:
        return default
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(f) or math.isinf(f):
        return default
    return f


def parse_rating_count(value: Any) -> int:
    if value is None or value == "" or str(value).strip().lower() in _MISSING_STRINGS:
        return 0
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0


def _attr_phrases(
    title: str,
    features: Sequence[str],
    details: Mapping[str, str],
    category_path: tuple[str, ...],
    is_sparse: bool,
) -> frozenset[str]:
    phrases: set[str] = set()
    for feat in features:
        n = normalise(feat)
        if is_indexable_phrase(n):
            phrases.add(n)
    for key in sorted(details.keys()):
        val = details[key]
        n = normalise(val)
        if is_indexable_phrase(n):
            phrases.add(n)
        kv = normalise(f"{key} {val}")
        if is_indexable_phrase(kv):
            phrases.add(kv)
    for cat in category_path:
        n = normalise(cat)
        if n and 1 <= len(n.split()) <= 8:
            phrases.add(n)
    if is_sparse:
        title_n = normalise(title)
        for gram in ngrams(title_n, 2, 4):
            if is_indexable_phrase(gram):
                phrases.add(gram)
    return frozenset(phrases)


@dataclass(frozen=True, slots=True)
class Product:
    parent_asin: str
    title: str
    text_blob: str
    leaf_category: str
    category_path: tuple[str, ...]
    attr_phrases: frozenset[str]
    details: Mapping[str, str]
    price: float | None
    avg_rating: float
    rating_count: int
    store: str
    is_sparse: bool


def product_from_record(record: Mapping[str, Any], sparse_threshold: int = 2) -> Product | None:
    asin = str(record.get("parent_asin") or record.get("asin") or "").strip()
    if not asin:
        return None
    title = str(record.get("title") or "").strip()
    features = parse_string_list(record.get("features"))
    description = clean_description(record.get("description"))
    categories = parse_string_list(record.get("categories"))
    details = parse_details(record.get("details"))
    price = parse_price(record.get("price"))
    avg_rating = parse_rating(record.get("average_rating", record.get("avg_rating")))
    rating_count = parse_rating_count(record.get("rating_number", record.get("rating_count")))
    store = str(record.get("store") or "").strip()

    category_path = tuple(categories)
    leaf_category = categories[-1] if categories else ""
    feat_desc_len = len(features) + (1 if description else 0)
    is_sparse = feat_desc_len < sparse_threshold

    blob_parts = [title, " ".join(features), description, " ".join(categories)]
    text_blob = normalise(" ".join(p for p in blob_parts if p))

    phrases = _attr_phrases(title, features, details, category_path, is_sparse)

    return Product(
        parent_asin=asin,
        title=title,
        text_blob=text_blob,
        leaf_category=leaf_category,
        category_path=category_path,
        attr_phrases=phrases,
        details=details,
        price=price,
        avg_rating=avg_rating,
        rating_count=rating_count,
        store=store,
        is_sparse=is_sparse,
    )


def _iter_json_records(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" or path.name.endswith(".jsonl.gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        first = fh.read(1)
        if not first:
            return
        fh.seek(0)
        if first == "[":
            data = json.load(fh)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        yield item
            return
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


@dataclass
class CatalogStore:
    products: tuple[Product, ...]
    asin_to_idx: dict[str, int]
    asins: tuple[str, ...]
    asin_codes: tuple[int, ...]
    popularity_idx: tuple[int, ...]
    phrase_to_docs: dict[str, tuple[int, ...]]
    phrase_idf: dict[str, float]
    leaf_categories: frozenset[str]
    category_phrases: tuple[str, ...]
    phrase_vocab: frozenset[str]

    def __len__(self) -> int:
        return len(self.products)

    def get(self, asin: str) -> Product | None:
        idx = self.asin_to_idx.get(asin)
        if idx is None:
            return None
        return self.products[idx]

    def popularity_asins(self) -> list[str]:
        return [self.asins[i] for i in self.popularity_idx]

    @classmethod
    def from_records(
        cls,
        records: Iterable[Mapping[str, Any]],
        sparse_threshold: int = 2,
    ) -> "CatalogStore":
        by_asin: dict[str, Product] = {}
        for rec in records:
            product = product_from_record(rec, sparse_threshold=sparse_threshold)
            if product is None:
                continue
            # Dedup on parent_asin only (TDD §3.2). First-seen wins so the
            # result does not depend on hash order of a set.
            if product.parent_asin not in by_asin:
                by_asin[product.parent_asin] = product

        # Deterministic product order: lexicographic parent_asin.
        asins = tuple(sorted(by_asin.keys()))
        products = tuple(by_asin[a] for a in asins)
        asin_to_idx = {a: i for i, a in enumerate(asins)}
        # asin_codes[i] is the lexicographic rank of asins[i] — which, because
        # `asins` is already sorted, is just i. Kept explicit for lexsort calls.
        asin_codes = tuple(range(len(asins)))

        popularity_idx = tuple(
            sorted(
                range(len(products)),
                key=lambda i: (
                    -products[i].rating_count,
                    -products[i].avg_rating,
                    products[i].parent_asin,
                ),
            )
        )

        buckets: dict[str, list[int]] = {}
        n_docs = len(products)
        for idx, product in enumerate(products):
            # Iterate a sorted tuple, never a set, so index construction is
            # independent of PYTHONHASHSEED.
            for phrase in sorted(product.attr_phrases):
                buckets.setdefault(phrase, []).append(idx)

        phrase_to_docs: dict[str, tuple[int, ...]] = {}
        phrase_idf: dict[str, float] = {}
        for phrase in sorted(buckets.keys()):
            docs = tuple(sorted(set(buckets[phrase])))
            phrase_to_docs[phrase] = docs
            df = len(docs)
            phrase_idf[phrase] = math.log((n_docs + 1.0) / (df + 1.0)) + 1.0

        leaves: set[str] = set()
        cat_set: set[str] = set()
        for product in products:
            if product.leaf_category:
                leaves.add(product.leaf_category)
            for cat in product.category_path:
                n = normalise(cat)
                if n:
                    cat_set.add(n)
        category_phrases = tuple(sorted(cat_set, key=lambda s: (-len(s), s)))

        return cls(
            products=products,
            asin_to_idx=asin_to_idx,
            asins=asins,
            asin_codes=asin_codes,
            popularity_idx=popularity_idx,
            phrase_to_docs=phrase_to_docs,
            phrase_idf=phrase_idf,
            leaf_categories=frozenset(sorted(leaves)),
            category_phrases=category_phrases,
            phrase_vocab=frozenset(phrase_to_docs.keys()),
        )

    @classmethod
    def load(cls, path: str | Path, sparse_threshold: int = 2) -> "CatalogStore":
        path = Path(path)
        return cls.from_records(_iter_json_records(path), sparse_threshold=sparse_threshold)
