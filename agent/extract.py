"""Constraint extraction for the Hybrid research path (TDD §5).

Submitted FastAgent uses `agent/parsing.py` instead. See README Limitations.
"""

from __future__ import annotations

from agent.catalog import CatalogStore
from agent.config import Config
from agent.lexicon import canonical_gender, expand_terms, guess_attribute
from agent.normalise import ngrams, normalise, token_count
from agent.state import SessionState
from agent.types import Constraint

# Whole-utterance only — "?" is stripped by normalise, and "what" must not
# match "what size" / "what's a good shirt".
_DECLINE_EXACT = frozenset({"?", "??", "???", "huh", "huh?", "what", "what?", "what??"})

_DECLINE_CUES = frozenset(
    {
        "no preference",
        "don't care",
        "dont care",
        "doesn't matter",
        "doesnt matter",
        "anything",
        "either is fine",
        "no opinion",
        "skip",
        "i don't know",
        "i dont know",
        "idk",
        "dunno",
        "no idea",
        "not sure",
        "whatever",
    }
)


class ConstraintExtractor:
    def __init__(self, catalog: CatalogStore, config: Config) -> None:
        self.catalog = catalog
        self.config = config
        self.semantic_fallback_fired = 0
        # Longest-first so "t shirts" wins over "shirts".
        self._category_phrases = catalog.category_phrases
        self._vocab = catalog.phrase_vocab

    def extract(
        self,
        utterance: str,
        state: SessionState,
        turn: int,
        encoder=None,
        phrase_embeddings=None,
    ) -> list[Constraint]:
        lexical_ok = self.config.exact_phrase_enabled
        normalised = normalise(utterance)
        if normalised == "shoe":
            normalised = "shoes"
        constraints: list[Constraint] = []

        if lexical_ok and normalised:
            constraints.extend(self._lexical(normalised, turn))
            constraints.extend(self._category(normalised, turn))
            constraints.extend(self._followup_slot(normalised, state, turn))
            constraints.extend(self._gender(normalised, turn))

        oov_ratio = self._oov_ratio(normalised)
        need_semantic = (
            self.config.force_semantic
            or len([c for c in constraints if c.source == "exact"])
            < self.config.semantic_fallback_threshold
            or oov_ratio >= self.config.oov_token_ratio
        )
        if need_semantic and encoder is not None and phrase_embeddings is not None:
            semantic = self._semantic(normalised, turn, encoder, phrase_embeddings)
            if semantic:
                self.semantic_fallback_fired += 1
                constraints.extend(semantic)

        return _dedupe_constraints(constraints)

    def utterance_is_decline(self, utterance: str) -> bool:
        raw = (utterance or "").strip().lower()
        if raw in _DECLINE_EXACT:
            return True
        n = normalise(utterance)
        if not n:
            return False
        cues = [normalise(c) for c in _DECLINE_CUES if c]
        if n in cues:
            return True
        padded = f" {n} "
        return any(f" {cue} " in padded for cue in cues)

    def _lexical(self, normalised: str, turn: int) -> list[Constraint]:
        hits: list[Constraint] = []
        seen: set[str] = set()
        windows = ngrams(normalised, 1, self.config.ngram_max)
        if 1 <= token_count(normalised) <= self.config.ngram_max:
            windows.append(normalised)
        windows.extend(expand_terms(normalised))
        for window in windows:
            if window in seen:
                continue
            if window in self._vocab:
                seen.add(window)
                hits.append(
                    Constraint(
                        text=window,
                        attribute=guess_attribute(window),
                        confidence=1.0,
                        source="exact",
                        turn=turn,
                    )
                )
        return hits

    def _category(self, normalised: str, turn: int) -> list[Constraint]:
        padded = f" {normalised} "
        for phrase in self._category_phrases:
            if len(phrase) < 3 or canonical_gender(phrase):
                continue
            if f" {phrase} " in padded:
                return [
                    Constraint(
                        text=phrase,
                        attribute="category",
                        confidence=1.0,
                        source="category",
                        turn=turn,
                    )
                ]
        # Whole-phrase only. "shirt" must not latch onto "blouses button-down shirts".
        expanded = set(expand_terms(normalised))
        for phrase in self._category_phrases:
            if canonical_gender(phrase):
                continue
            if phrase in expanded:
                return [
                    Constraint(
                        text=phrase,
                        attribute="category",
                        confidence=0.9,
                        source="category",
                        turn=turn,
                    )
                ]
        return []

    def _gender(self, normalised: str, turn: int) -> list[Constraint]:
        gender = canonical_gender(normalised)
        if not gender:
            return []
        return [
            Constraint(
                text=gender,
                attribute="department",
                confidence=1.0,
                source="exact",
                turn=turn,
            )
        ]

    def _oov_ratio(self, normalised: str) -> float:
        tokens = normalised.split()
        if not tokens:
            return 0.0
        # A token is in-vocab if it appears in any indexed phrase.
        # Approximate with a cheap membership: phrase vocab is full phrases,
        # so we also treat single-token phrases and token-in-phrase via a
        # precomputed token set if available. Fall back to phrase membership.
        unknown = 0
        for tok in tokens:
            if tok in self._vocab:
                continue
            # token may still be part of a multi-word phrase; don't count as OOV
            # solely on that. OOV here means "never seen as its own phrase".
            unknown += 1
        return unknown / len(tokens)

    def _semantic(
        self,
        normalised: str,
        turn: int,
        encoder,
        phrase_embeddings,
    ) -> list[Constraint]:
        if not normalised:
            return []
        try:
            import numpy as np

            from agent.determinism import topk_indices

            vec = encoder.encode([normalised])[0]
            norm = float(np.linalg.norm(vec))
            if norm == 0.0:
                return []
            vec = vec / norm
            scores = phrase_embeddings.matrix @ vec
            k = min(8, scores.shape[0])
            order = topk_indices(scores, phrase_embeddings.codes, k)
            out: list[Constraint] = []
            floor = self.config.semantic_cosine_floor
            for idx in order:
                score = float(scores[int(idx)])
                if score < floor:
                    continue
                phrase = phrase_embeddings.phrases[int(idx)]
                out.append(
                    Constraint(
                        text=phrase,
                        attribute=guess_attribute(phrase),
                        confidence=max(0.0, min(1.0, score)),
                        source="semantic",
                        turn=turn,
                    )
                )
            return out
        except Exception:
            return []


    def _followup_slot(self, normalised: str, state: SessionState, turn: int) -> list[Constraint]:
        """Short answers after we asked something ('brown', 'eu40') become a slot."""
        n_tok = token_count(normalised)
        if not normalised or n_tok == 0:
            return []
        guessed = guess_attribute(normalised)
        if n_tok <= 2 and guessed:
            attr = guessed
        elif state.asked and n_tok <= 4:
            attr = guessed or state.asked[-1]
        else:
            return []
        if attr in {"other", "category"}:
            return []
        text = canonical_gender(normalised) if attr in {"style", "department"} else normalised
        return [
            Constraint(
                text=text or normalised,
                attribute=attr,
                confidence=0.95 if guessed else 0.8,
                source="exact",
                turn=turn,
            )
        ]


def _dedupe_constraints(constraints: list[Constraint]) -> list[Constraint]:
    """Keep highest-confidence per (text, source), preserve first-seen order."""
    best: dict[tuple[str, str], Constraint] = {}
    order: list[tuple[str, str]] = []
    for c in constraints:
        key = (c.text, c.source)
        if key not in best:
            order.append(key)
            best[key] = c
        elif c.confidence > best[key].confidence:
            best[key] = c
    return [best[k] for k in order]
