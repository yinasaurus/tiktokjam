"""Per-turn wall-clock budget (FR-20, TDD §11). Checked between stages only."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TurnBudget:
    soft_ms: float = 450.0
    hard_ms: float = 500.0
    safety_margin_ms: float = 8.0
    t0: float = 0.0

    def __post_init__(self) -> None:
        if self.t0 == 0.0:
            self.t0 = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.t0) * 1000.0

    def remaining_ms(self) -> float:
        return self.hard_ms - self.elapsed_ms()

    def can_afford(self, cost_ms: float) -> bool:
        return self.remaining_ms() > (cost_ms + self.safety_margin_ms)

    def rung(self) -> str:
        rem = self.remaining_ms()
        if rem > 250:
            return "full"
        if rem > 100:
            return "ltr_only"
        if rem > 40:
            return "fused"
        if rem > 10:
            return "no_dense"
        return "cached"
