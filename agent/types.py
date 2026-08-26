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
    "total_tokens": 0,
}
