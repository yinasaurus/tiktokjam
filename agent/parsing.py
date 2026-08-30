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


@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind
    category: str | None = None
    constraints: tuple[str, ...] = ()
    attribute: str | None = None
    scenario_hint: str | None = None


def parse_event(message: str) -> Event:
    text = (message or "").strip()
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
        return Event(kind="override", constraints=(match.group("new").strip(),))

    match = _DISCLOSURE_RE.match(text)
    if match:
        return Event(kind="disclosure", constraints=_split_disclosure(match.group("values")))

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


def _split_disclosure(values: str) -> tuple[str, ...]:
    # The simulator joins up to two constraints with "; ". Constraint text may
    # contain semicolons, so split only on the exact join token.
    parts = [part.strip() for part in values.split("; ") if part.strip()]
    return tuple(parts)
