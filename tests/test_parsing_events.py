from __future__ import annotations

from agent.parsing import parse_event


def test_parse_buying_opening():
    event = parse_event("I'm looking for Hoop. A key requirement is: Spandex.")
    assert event.kind == "opening"
    assert event.category == "Hoop"
    assert event.constraints == ("Spandex",)
    assert event.scenario_hint == "buying"


def test_parse_browsing_opening():
    event = parse_event("I'm looking for Shirts T Shirts, but I'm still exploring.")
    assert event.kind == "opening"
    assert event.category == "Shirts T Shirts"
    assert event.constraints == ()
    assert event.scenario_hint == "browsing"


def test_parse_intent_override_opening():
    event = parse_event("I'm looking for Shoes. Prefer something black.")
    assert event.kind == "opening"
    assert event.category == "Shoes"
    assert event.constraints == ("Prefer something black.",)
    assert event.scenario_hint == "intent_override"


def test_parse_override():
    event = parse_event("Actually, ignore my earlier preference. What I need is: leather.")
    assert event.kind == "override"
    assert event.constraints == ("leather",)


def test_parse_disclosure_with_dollar_and_semicolon_join():
    event = parse_event("For that, what matters is: budget around $19.99; cotton.")
    assert event.kind == "disclosure"
    assert event.constraints == ("budget around $19.99", "cotton")


def test_parse_refusals_and_rebuke():
    assert parse_event("I don't have an additional preference for material.").kind == "exhausted"
    assert parse_event("I don't have a preference for color; please use your judgment.").kind == "no_preference"
    assert (
        parse_event("Those options are not quite right yet. Ask me about one specific attribute.").kind
        == "rebuke"
    )


def test_parse_reordered_buying_opening():
    event = parse_event(
        "A key requirement is: Material:alloy. I'm looking for Jewelry Necklaces if that makes sense"
    )
    assert event.kind == "opening"
    assert event.category == "Jewelry Necklaces"
    assert event.constraints == ("Material:alloy",)
    assert event.scenario_hint == "buying"


def test_parse_reordered_override_opening():
    event = parse_event("Buckle closure. I'm looking for Accessories Belts if that makes sense")
    assert event.kind == "opening"
    assert event.category == "Accessories Belts"
    assert event.constraints == ("Buckle closure",)
    assert event.scenario_hint == "intent_override"


def test_parse_reordered_disclosure():
    event = parse_event("um, What matters is: leather; 100% Leather, for that")
    assert event.kind == "disclosure"
    assert event.constraints == ("leather", "100% Leather")


def test_parse_reordered_override():
    event = parse_event(
        "What I need is: leather. Actually, ignore my earlier preference if that makes sense"
    )
    assert event.kind == "override"
    assert event.constraints == ("leather",)


def test_parse_reordered_browsing_opening():
    event = parse_event("um, I'm still exploring, but I'm looking for Basketball Men")
    assert event.kind == "opening"
    assert event.category == "Basketball Men"
    assert event.constraints == ()
    assert event.scenario_hint == "browsing"
