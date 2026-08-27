"""Lexicon aliases used at index and query time."""

from __future__ import annotations

from agent.lexicon import canonical_gender, expand_terms, guess_attribute


def test_gender_phrases():
    assert canonical_gender("male") == "men"
    assert canonical_gender("for him") == "men"
    assert canonical_gender("boyfriend") == "men"
    assert canonical_gender("for her") == "women"
    assert canonical_gender("ladies") == "women"
    assert canonical_gender("blue shirt") is None


def test_expand_type_aliases():
    sneakers = set(expand_terms("sneakers"))
    assert "fashion sneakers" in sneakers
    blouse = set(expand_terms("blouse"))
    assert "blouses button-down shirts" in blouse
    shirt = set(expand_terms("shirt"))
    assert "t-shirts" in shirt
    assert "blouses button-down shirts" not in shirt


def test_guess_new_slots():
    assert guess_attribute("charcoal") == "color"
    assert guess_attribute("chiffon") == "material"
    assert guess_attribute("gym") == "use_case"
    assert guess_attribute("slim") == "style"
    assert guess_attribute("floral") == "feature"
    assert guess_attribute("large") == "size"
