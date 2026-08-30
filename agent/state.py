"""Dialog state manager (TDD §6). All session state lives here, keyed by session_id."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from agent.config import Config
from agent.types import Constraint, SlotValue

Intent = Literal["buying", "browsing", "unknown"]


@dataclass
class SessionState:
    session_id: str
    user_profile: dict[str, Any]
    turn: int = 0
    leaf_category: str | None = None
    intent: Intent = "unknown"
    slots: dict[str, SlotValue] = field(default_factory=dict)
    free_constraints: list[Constraint] = field(default_factory=list)
    disclosed_texts: list[str] = field(default_factory=list)
    asked: list[str] = field(default_factory=list)  # list, not set — ranking-safe
    declined: list[str] = field(default_factory=list)
    last_candidates: list[str] = field(default_factory=list)
    last_query_vec: Any = None
    last_utterance: str = ""

    def asked_set(self) -> frozenset[str]:
        return frozenset(self.asked)

    def declined_set(self) -> frozenset[str]:
        return frozenset(self.declined)

    def mark_asked(self, attribute: str) -> None:
        if attribute not in self.asked:
            self.asked.append(attribute)

    def mark_declined(self, attribute: str) -> None:
        if attribute not in self.declined:
            self.declined.append(attribute)

    def remember_disclosures(self, values: tuple[str, ...]) -> None:
        for value in values:
            text = str(value).strip()
            if text and text not in self.disclosed_texts:
                self.disclosed_texts.append(text)


class DialogStateManager:
    def __init__(self, config: Config) -> None:
        self.config = config

    def apply(self, state: SessionState, constraints: list[Constraint], turn: int) -> SessionState:
        state.turn = turn
        retain = self.config.retain_superseded

        for constraint in constraints:
            if constraint.source == "category" and constraint.text:
                new_leaf = constraint.text
                if state.leaf_category and new_leaf != state.leaf_category:
                    # Full override: category change. Clear slots, keep history.
                    for slot in state.slots.values():
                        if retain and slot.value not in slot.superseded:
                            slot.superseded.append(slot.value)
                    state.slots = {}
                state.leaf_category = new_leaf
                continue

            attr = constraint.attribute
            if attr is None:
                state.free_constraints.append(constraint)
                continue

            existing = state.slots.get(attr)
            if existing is None:
                state.slots[attr] = SlotValue(
                    value=constraint.text,
                    confidence=constraint.confidence,
                    set_at_turn=turn,
                )
            elif existing.value != constraint.text:
                # Partial override — other slots persist (FR-17).
                if retain and existing.value not in existing.superseded:
                    existing.superseded.append(existing.value)
                existing.value = constraint.text
                existing.confidence = constraint.confidence
                existing.set_at_turn = turn
            else:
                existing.confidence = max(existing.confidence, constraint.confidence)
                existing.set_at_turn = turn

        return state

    def active_constraints(self, state: SessionState) -> list[Constraint]:
        """Flatten slots + free constraints for retrieval query construction.

        Decay is applied here from the stored base confidence
        (weight = base × decay^(turn − set_turn)), never by mutating the slot.
        """
        decay = self.config.confidence_decay
        out: list[Constraint] = []
        for attr in sorted(state.slots.keys()):
            slot = state.slots[attr]
            age = max(0, state.turn - slot.set_at_turn)
            weight = slot.confidence * (decay**age)
            out.append(
                Constraint(
                    text=slot.value,
                    attribute=attr,
                    confidence=weight,
                    source="exact",
                    turn=slot.set_at_turn,
                )
            )
            if self.config.retain_superseded:
                for old in slot.superseded:
                    out.append(
                        Constraint(
                            text=old,
                            attribute=attr,
                            confidence=weight * 0.4,
                            source="exact",
                            turn=slot.set_at_turn,
                        )
                    )
        out.extend(state.free_constraints)
        if state.leaf_category:
            out.append(
                Constraint(
                    text=state.leaf_category,
                    attribute="category",
                    confidence=1.0,
                    source="category",
                    turn=state.turn,
                )
            )
        return out
