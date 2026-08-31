"""Parse deterministic simulator messages into structured dialog events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

EventKind = Literal[
    "opening",
    "override",
    "disclosure",
    "exhausted",
    "no_preference",
    "rebuke",
    "unknown",
]

_OPEN_BUYING_RE = re.compile(
    r"^I'm looking for (?P<category>.+?)\. A key requirement is: (?P<constraint>.+)\.$"
)
_OPEN_BROWSING_RE = re.compile(
    r"^I'm looking for (?P<category>.+?), but I'm still exploring\.$"
)
_OPEN_OVERRIDE_RE = re.compile(r"^I'm looking for (?P<category>.+?)\. (?P<old>.+)$")
_OVERRIDE_RE = re.compile(
    r"^Actually, ignore my earlier preference\. What I need is: (?P<new>.+)\.$"
)
_DISCLOSURE_RE = re.compile(r"^For that, what matters is: (?P<values>.+)\.$")
_EXHAUSTED_RE = re.compile(r"^I don't have an additional preference for (?P<attr>.+)\.$")
_NO_PREF_RE = re.compile(
    r"^I don't have a preference for (?P<attr>.+?); please use your judgment\.$"
)
_REBUKE = "Those options are not quite right yet. Ask me about one specific attribute."

# Conservative discourse markers only — do not strip content words.
_FILLER_RES = (
    re.compile(r"\bum,", re.IGNORECASE),
    re.compile(r"\bif that makes sense\b", re.IGNORECASE),
    re.compile(r"\bi guess\b", re.IGNORECASE),
)

_LOOKING_FOR = re.compile(
    r"I'm looking for (?P<category>.+?)(?:\.(?:\s|$)|, but |, |$)",
    re.IGNORECASE,
)
_KEY_REQUIREMENT = re.compile(
    r"A key requirement is:\s*(?P<constraint>.+?)(?:\.(?:\s|$)|$)",
    re.IGNORECASE,
)
_NEED = re.compile(
    r"What I need is:\s*(?P<new>.+?)(?:\.(?:\s|$)|$)",
    re.IGNORECASE,
)
_IGNORE = re.compile(r"ignore my earlier preference", re.IGNORECASE)
_MATTERS = re.compile(
    r"(?:For that,\s*)?what matters is:\s*(?P<values>.+?)(?:\s*,\s*for that\s*|\.(?:\s|$)|$)",
    re.IGNORECASE,
)
_EXHAUSTED_LOOSE = re.compile(
    r"I don't have an additional preference for (?P<attr>.+?)(?:\.(?:\s|$)|$)",
    re.IGNORECASE,
)
_NO_PREF_LOOSE = re.compile(
    r"I don't have a preference for (?P<attr>.+?)(?:;|\.(?:\s|$)|$)",
    re.IGNORECASE,
)
_JUDGMENT = re.compile(r"please use your judgment", re.IGNORECASE)
_STILL_EXPLORING = re.compile(r"still exploring", re.IGNORECASE)
_REBUKE_A = re.compile(r"those options are not quite right yet", re.IGNORECASE)
_REBUKE_B = re.compile(r"ask me about one specific attribute", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    category: str | None = None
    constraints: tuple[str, ...] = ()
    attribute: str | None = None
    scenario_hint: str | None = None


def normalize_utterance(message: str) -> str:
    """Strip a short, conservative list of filler/discourse markers."""
    text = (message or "").strip()
    for pattern in _FILLER_RES:
        text = pattern.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",{2,}", ",", text)
    return text.strip(" ,")


def parse_event(message: str) -> Event:
    text = (message or "").strip()
    exact = _parse_anchored(text)
    if exact.kind != "unknown":
        return exact

    normalized = normalize_utterance(text)
    if normalized != text:
        exact = _parse_anchored(normalized)
        if exact.kind != "unknown":
            return exact
    return _parse_order_invariant(normalized)


def _parse_anchored(text: str) -> Event:
    if text == _REBUKE:
        return Event(kind="rebuke")

    match = _OPEN_BUYING_RE.match(text)
    if match:
        return Event(
            kind="opening",
            category=match.group("category").strip(),
            constraints=(match.group("constraint").strip(),),
            scenario_hint="buying",
        )

    match = _OPEN_BROWSING_RE.match(text)
    if match:
        return Event(
            kind="opening",
            category=match.group("category").strip(),
            scenario_hint="browsing",
        )

    match = _OVERRIDE_RE.match(text)
    if match:
        return Event(
            kind="override",
            constraints=(match.group("new").strip(),),
        )

    match = _DISCLOSURE_RE.match(text)
    if match:
        return Event(
            kind="disclosure",
            constraints=_split_disclosure(match.group("values")),
        )

    match = _EXHAUSTED_RE.match(text)
    if match:
        return Event(kind="exhausted", attribute=match.group("attr").strip())

    match = _NO_PREF_RE.match(text)
    if match:
        return Event(kind="no_preference", attribute=match.group("attr").strip())

    match = _OPEN_OVERRIDE_RE.match(text)
    if match:
        return Event(
            kind="opening",
            category=match.group("category").strip(),
            constraints=(match.group("old").strip(),),
            scenario_hint="intent_override",
        )

    return Event(kind="unknown")


def _parse_order_invariant(text: str) -> Event:
    """Search the full utterance for each event pattern independently."""
    looking = _LOOKING_FOR.search(text)
    key_req = _KEY_REQUIREMENT.search(text)
    need = _NEED.search(text)
    ignore = _IGNORE.search(text)
    matters = _MATTERS.search(text)
    exhausted = _EXHAUSTED_LOOSE.search(text)
    no_pref = _NO_PREF_LOOSE.search(text)
    exploring = _STILL_EXPLORING.search(text)
    rebuke = _REBUKE_A.search(text) and _REBUKE_B.search(text)

    category = looking.group("category").strip() if looking else None

    # Override marker and its constraint are independent: finding one must not
    # suppress the other.
    if ignore:
        constraints: tuple[str, ...] = ()
        if need:
            constraints = (need.group("new").strip(),)
        return Event(kind="override", category=category, constraints=constraints)

    if looking and key_req:
        return Event(
            kind="opening",
            category=category,
            constraints=(key_req.group("constraint").strip(),),
            scenario_hint="buying",
        )

    if looking and exploring:
        return Event(
            kind="opening",
            category=category,
            scenario_hint="browsing",
        )

    if looking:
        leftover = _leftover_constraint(text, category or "")
        return Event(
            kind="opening",
            category=category,
            constraints=(leftover,) if leftover else (),
            scenario_hint="intent_override",
        )

    if matters:
        return Event(
            kind="disclosure",
            constraints=_split_disclosure(matters.group("values")),
        )

    if exhausted:
        return Event(kind="exhausted", attribute=exhausted.group("attr").strip())

    if no_pref and _JUDGMENT.search(text):
        return Event(kind="no_preference", attribute=no_pref.group("attr").strip())

    if rebuke:
        return Event(kind="rebuke")

    return Event(kind="unknown")


def _leftover_constraint(text: str, category: str) -> str | None:
    leftover = text
    if category:
        leftover = re.sub(
            r"I'm looking for\s+" + re.escape(category),
            " ",
            leftover,
            flags=re.IGNORECASE,
        )
    leftover = _STILL_EXPLORING.sub(" ", leftover)
    leftover = re.sub(r"\bI'm\b", " ", leftover, flags=re.IGNORECASE)
    leftover = re.sub(r"\bbut\b", " ", leftover, flags=re.IGNORECASE)
    leftover = leftover.strip(" .,;:")
    return leftover or None


def _split_disclosure(values: str) -> tuple[str, ...]:
    # The simulator joins up to two constraints with "; ". Constraint text may
    # contain semicolons, so split only on the exact join token.
    parts = [part.strip(" ,") for part in values.split("; ") if part.strip(" ,")]
    return tuple(parts)
