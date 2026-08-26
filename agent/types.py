"""Shared types used across components. No numpy, no catalog I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ConstraintSource = Literal["exact", "semantic", "category", "profile"]


@dataclass(frozen=True, slots=True)
class Constraint:
    text: str
    attribute: str | None
    confidence: float
    source: ConstraintSource
    turn: int


@dataclass
class SlotValue:
    value: str
    confidence: float
    set_at_turn: int
    superseded: list[str] = field(default_factory=list)


ZERO_USAGE: dict[str, int] = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
}


def asins_of(response: dict) -> list[str]:
    """Pull parent_asin strings from an official recommendations payload."""
    out: list[str] = []
    for item in response.get("recommendations") or []:
        if isinstance(item, dict):
            asin = str(item.get("parent_asin") or "").strip()
        else:
            asin = str(item).strip()
        if asin:
            out.append(asin)
    return out


def payload(message: str, ask_attribute: str | None, asins: list[str]) -> dict:
    """Official turn_response shape from docs/agent_api_contract.json."""
    return {
        "message": message,
        "ask_attribute": ask_attribute,
        "recommendations": [{"parent_asin": asin} for asin in asins],
        "usage": dict(ZERO_USAGE),
    }
