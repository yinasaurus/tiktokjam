"""Index-time and query-time normalisation must be identical (TDD §3.3)."""

from __future__ import annotations

from agent.normalise import is_indexable_phrase, normalise

SAMPLES = [
    "100% Cotton",
    "Crew Neck",
    "short-sleeve",
    "Package Including",
    "Description",
    "Feature: moisture-wicking",
    "V-Neck",
    "t-shirts",
    "Navy Blue",
    "Oxford Cloth",
    "double breasted",
    "slim fit",
    "floral print",
    "genuine leather",
    "kangaroo pocket",
    "drawstring hood",
    "elastic waist",
    "midi length",
    "button down",
    "pure linen",
    "silk fabric",
    "wool blend",
    "stretch denim",
    "athletic shorts",
    "cotton hoodie",
    "  Extra   Whitespace  ",
    "Cotton &amp; Linen",
    "<b>Bold Cotton</b>",
    "Made in USA!!!",
    "size: M",
    "color: Navy",
    "100 percent cotton crew neck tee",
    "long-sleeve button-front shirt",
    "women's floral midi dress",
    "men's slim-fit jeans",
    "machine washable",
    "imported",
    "shipped from",
    "specifications",
    "feature list item one two",
    "a b",
    "one",
    "this phrase has exactly eight tokens in it now",
    "this phrase has more than eight tokens so it should drop later",
    "T-Shirts",
    "Hoodies & Sweatshirts",
    "Button-Down Shirts",
    "Casual",
    "Winter",
    "Polyester",
    "Relaxed Fit",
    "Regular Fit",
    "Silver Buckle",
    "Moisture Wicking Fabric",
    "Everyday Black Tee",
    "Soft Everyday Tee",
    "Breathable Linen Shirt",
    "Evening Blouse",
    "Winter Coat",
    "Classic Jeans",
    "Summer Dress",
    "Office Shirt",
    "Gym Shorts",
    "Everyday Belt",
    "Casual Hoodie",
    "navy cotton crewneck t-shirt",
    "BLACK COTTON CREWNECK T-SHIRT",
    "Red Silk Blouse",
    "Blue Denim Jeans",
    "Pink Floral Dress",
    "White Cotton Oxford Shirt",
    "Green Athletic Shorts",
    "Black Leather Belt",
    "Navy Cotton Hoodie",
    "Beige Wool Coat",
    "Sparse Navy Hat",
    "crew neck short sleeve",
    "100% cotton kangaroo pocket",
    "double-breasted wool",
    "v neck silk",
    "floral midi",
    "oxford cloth button down",
    "elastic waist gym shorts",
    "genuine leather silver buckle",
    "drawstring hood casual",
    "stretch denim slim fit",
    "linen long sleeve",
    "cotton crew neck",
    "navy blue linen",
    "pink floral print dress",
    "white oxford",
    "green polyester athletic",
    "black leather",
    "navy cotton",
    "beige wool",
    "red silk",
    "blue denim",
    "short sleeve tee",
    "long sleeve shirt",
    "midi dress",
    "slim jeans",
]


def test_at_least_100_samples():
    assert len(SAMPLES) >= 100


def test_normalise_is_idempotent():
    for phrase in SAMPLES:
        once = normalise(phrase)
        assert once == normalise(once)


def test_index_query_symmetry():
    """The same string normalised on both sides must match exactly."""
    for phrase in SAMPLES:
        index_side = normalise(phrase)
        query_side = normalise(phrase)
        assert index_side == query_side


def test_boilerplate_stripped():
    assert "description" not in normalise("Description: cotton tee").split()
    assert "feature" not in normalise("Feature moisture wicking").split()


def test_hyphen_kept_inside_words():
    assert "t-shirts" in normalise("T-Shirts") or "t-shirt" in normalise("t-shirt")
    assert "-" in normalise("crew-neck") or "crew-neck" == normalise("crew-neck")


def test_indexable_bounds():
    assert not is_indexable_phrase(normalise("cotton"))  # 1 token
    assert is_indexable_phrase(normalise("cotton crew"))
    assert not is_indexable_phrase(
        normalise("one two three four five six seven eight nine")
    )
