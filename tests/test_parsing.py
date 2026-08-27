"""FR-21 — defensive catalog field parsing, including the literal \"None\" sentinel."""

from __future__ import annotations

import math

from agent.catalog import parse_details, parse_price, parse_string_list, product_from_record


def test_price_literal_none():
    assert parse_price("None") is None
    assert parse_price("none") is None
    assert parse_price("NONE") is None


def test_price_empty_and_missing():
    assert parse_price("") is None
    assert parse_price(None) is None
    assert parse_price("n/a") is None


def test_price_range_takes_low_end():
    assert parse_price("$12.99 - $19.99") == 12.99
    assert parse_price("12.99-19.99") == 12.99


def test_price_currency_and_float():
    assert parse_price("$18.50") == 18.50
    assert parse_price(19.99) == 19.99
    assert parse_price(0) == 0.0


def test_price_never_raises_on_garbage():
    assert parse_price("free") is None
    assert parse_price("abc") is None
    assert parse_price(float("nan")) is None
    assert parse_price(math.inf) is None
    assert parse_price(True) is None


def test_details_json_string():
    parsed = parse_details('{"Color": "Red", "Material": "Silk"}')
    assert parsed["color"] == "Red"
    assert parsed["material"] == "Silk"


def test_details_dict_and_none():
    assert parse_details({"Color": "Navy"}) == {"color": "Navy"}
    assert parse_details(None) == {}
    assert parse_details("") == {}
    assert parse_details("not-json") == {}
    assert parse_details(123) == {}


def test_features_coerce_non_strings():
    assert parse_string_list([1, "cotton", None, ""]) == ["1", "cotton"]


def test_product_from_record_survives_bad_fields():
    product = product_from_record(
        {
            "parent_asin": "X1",
            "title": "Thing",
            "features": [None, 12],
            "description": ["Description", "Nice"],
            "price": "None",
            "categories": [],
            "details": None,
            "average_rating": "n/a",
            "rating_number": "",
            "store": None,
        }
    )
    assert product is not None
    assert product.price is None
    assert product.avg_rating == 0.0
    assert product.rating_count == 0
    assert product.details == {}
    assert "description" not in product.text_blob
    assert product.features == ("12",)
    assert "Nice" in product.description


def test_missing_asin_dropped():
    assert product_from_record({"title": "no asin"}) is None
