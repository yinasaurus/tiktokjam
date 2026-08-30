"""M0 helper: per-field missingness on the 50k slice (PRD A4)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.catalog import CatalogStore, parse_details, parse_price, parse_string_list


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    args = parser.parse_args()

    print(f"loading catalog: {args.catalog}", flush=True)
    store = CatalogStore.load_cached(args.catalog)
    print("catalog normalised", flush=True)
    n = len(store)
    missing = Counter()
    price_none_literal = 0
    details_as_string = 0
    sparse = 0
    feat_desc_lens: list[int] = []

    # Re-read raw records so we can see the literal "None" before parsing.
    opener = args.catalog.open
    print("reading raw records for missingness", flush=True)
    with opener(encoding="utf-8") as fh:
        first = fh.read(1)
        fh.seek(0)
        records: list[dict]
        if first == "[":
            records = json.load(fh)
        else:
            records = [json.loads(line) for line in fh if line.strip()]

    print(f"measuring {len(records)} raw records", flush=True)
    for i, rec in enumerate(records, start=1):
        if rec.get("price") == "None":
            price_none_literal += 1
        if isinstance(rec.get("details"), str):
            details_as_string += 1
        if not rec.get("title"):
            missing["title"] += 1
        if not parse_string_list(rec.get("features")):
            missing["features"] += 1
        if not parse_string_list(rec.get("description")):
            missing["description"] += 1
        if parse_price(rec.get("price")) is None:
            missing["price"] += 1
        if not parse_string_list(rec.get("categories")):
            missing["categories"] += 1
        if not parse_details(rec.get("details")):
            missing["details"] += 1
        feat_desc_lens.append(
            len(parse_string_list(rec.get("features")))
            + (1 if parse_string_list(rec.get("description")) else 0)
        )
        if i % 10000 == 0:
            print(f"  measured {i} records", flush=True)

    sparse = sum(1 for p in store.products if p.is_sparse)
    feat_desc_lens.sort()
    p10 = feat_desc_lens[max(0, int(0.1 * len(feat_desc_lens)) - 1)] if feat_desc_lens else 0

    print(f"n={n}")
    print(f"price literal 'None': {price_none_literal} ({price_none_literal / max(n, 1):.1%})")
    print(f"details delivered as JSON string: {details_as_string}")
    print(f"sparse (current threshold): {sparse}")
    print(f"feat+desc length 10th percentile: {p10}  ← candidate sparse_threshold")
    print("missing / empty after parse:")
    for field in ("title", "features", "description", "price", "categories", "details"):
        print(f"  {field:12} {missing[field]:6d}  {missing[field] / max(n, 1):.1%}")


if __name__ == "__main__":
    main()
