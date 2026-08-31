"""Not the submitted agent — see README Limitations.

Hybrid orchestration + deadline guard (research path). The official
evaluator does `from starter.agent import Agent`, which is FastAgent
(`agent/fast_agent.py`). This module remains as HybridAgent for documented
future work.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any

from agent.budget import TurnBudget
from agent.catalog import CatalogStore
from agent.config import Config
from agent.determinism import pin_runtime
from agent.extract import ConstraintExtractor
from agent.fusion import backfill_popularity, fuse
from agent.parsing import parse_event
from agent.question import choose_ask_attribute
from agent.rerank import rerank
from agent.routes.dense import DenseIndex, HashEncoder, load_encoder
from agent.routes.exact_phrase import ExactPhraseIndex
from agent.routes.lexical import LexicalIndex
from agent.state import DialogStateManager, SessionState
from agent.types import Constraint, payload

pin_runtime()

_CATALOG_CANDIDATES = (
    "SHOPPING_AGENT_CATALOG",
    "CATALOG_PATH",
)


def _discover_catalog_path() -> Path | None:
    for env in _CATALOG_CANDIDATES:
        raw = os.environ.get(env)
        if raw:
            p = Path(raw)
            if p.exists():
                return p
    here = Path.cwd()
    for rel in (
        Path("data/catalog.jsonl"),
        Path("data/catalog.json"),
        Path("data/amazon_clothing.jsonl"),
        Path("catalog.jsonl"),
        Path("tests/fixtures/catalog.jsonl"),
    ):
        p = here / rel
        if p.exists():
            return p
    return None


class Agent:
    """Offline multi-turn shopping agent.

    Contract (C-2):
        reset(session_id, user_profile)
        respond(session_id, user_message, turn, top_k) -> dict
    """

    def __init__(
        self,
        catalog: CatalogStore | list | str | Path | None = None,
        config: Config | None = None,
        encoder=None,
    ) -> None:
        self.config = config or Config()
        self.catalog = self._load_catalog(catalog)
        self._sessions: dict[str, SessionState] = {}
        self._state_mgr = DialogStateManager(self.config)
        self.extractor = ConstraintExtractor(self.catalog, self.config)
        self.exact = ExactPhraseIndex(self.catalog, self.config)
        self.lexical = LexicalIndex(self.catalog, self.config)
        if encoder is None:
            encoder = load_encoder(self.config)
        if encoder is None and self.config.dense_enabled and len(self.catalog) <= 256:
            # Tiny catalogs (unit tests): keep the dense route wired.
            # Do not HashEncoder the 50k official catalog — wait for models/encoder.
            encoder = HashEncoder(dim=64)
        self.encoder = encoder
        self.dense = DenseIndex(self.catalog, self.config, encoder=encoder)
        self.metrics: dict[str, Any] = {
            "semantic_fallback_fired": 0,
            "empty_pool_recoveries": 0,
            "budget_degradations": Counter(),
            "ask_attribute_selected": Counter(),
        }

    def _load_catalog(self, catalog: CatalogStore | list | str | Path | None) -> CatalogStore:
        if isinstance(catalog, CatalogStore):
            return catalog
        if isinstance(catalog, list):
            return CatalogStore.from_records(
                catalog, sparse_threshold=self.config.sparse_threshold
            )
        path: Path | None
        if isinstance(catalog, (str, Path)):
            path = Path(catalog)
        else:
            path = _discover_catalog_path()
        if path is None:
            raise FileNotFoundError(
                "No catalog found. Pass catalog=... or set SHOPPING_AGENT_CATALOG."
            )
        return CatalogStore.load_cached(
            path,
            sparse_threshold=self.config.sparse_threshold,
            cache_dir=self.config.cache_dir,
        )

    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        self._sessions[session_id] = SessionState(
            session_id=session_id,
            user_profile=dict(user_profile or {}),
        )

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int = 10,
    ) -> dict:
        budget = TurnBudget(
            soft_ms=self.config.soft_budget_ms,
            hard_ms=self.config.hard_budget_ms,
            safety_margin_ms=self.config.safety_margin_ms,
        )
        try:
            return self._respond_inner(session_id, user_message, turn, top_k, budget)
        except Exception:
            return self._degraded_response(session_id, top_k, "internal error; degraded")

    def _respond_inner(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
        budget: TurnBudget,
    ) -> dict:
        top_k = max(1, int(top_k))
        state = self._sessions.get(session_id)
        if state is None:
            state = SessionState(session_id=session_id, user_profile={})
            self._sessions[session_id] = state

        if budget.rung() == "cached":
            self.metrics["budget_degradations"]["cached"] += 1
            return self._degraded_response(session_id, top_k, "budget exhausted")

        state.last_utterance = user_message or ""
        event = parse_event(user_message or "")
        if event.kind == "override":
            state.slots = {}
            state.free_constraints = []
            state.disclosed_texts = []
            state.last_query_vec = None
        if event.constraints:
            state.remember_disclosures(event.constraints)
        if self.extractor.utterance_is_decline(user_message) and state.asked:
            state.mark_declined(state.asked[-1])

        phrase_table = self.dense.phrase_table if self.dense.available else None
        use_semantic = (
            self.dense.available
            and phrase_table is not None
            and budget.can_afford(40)
        )
        try:
            constraints = self.extractor.extract(
                user_message or "",
                state,
                turn,
                encoder=self.encoder if use_semantic else None,
                phrase_embeddings=phrase_table if use_semantic else None,
            )
        except Exception:
            constraints = []
        self.metrics["semantic_fallback_fired"] = self.extractor.semantic_fallback_fired
        self._state_mgr.apply(state, constraints, turn)
        active = self._state_mgr.active_constraints(state)

        skip_dense = budget.rung() in {"no_dense", "cached"} or not budget.can_afford(40)
        if skip_dense and self.config.dense_enabled:
            self.metrics["budget_degradations"]["no_dense"] += 1

        route_hits = self._run_routes(active, user_message or "", state, skip_dense)
        try:
            fused = fuse(route_hits, self.config, n_fuse=max(self.config.N_fuse, top_k))
        except Exception:
            fused = []

        if len(fused) < top_k:
            fused = self._recover_empty_pool(
                fused, active, user_message or "", state, skip_dense, top_k
            )

        skip_rerank = budget.rung() in {"fused", "no_dense", "cached"} or not budget.can_afford(30)
        if skip_rerank:
            self.metrics["budget_degradations"][budget.rung()] += 1
            ranked = fused
        else:
            try:
                ranked = rerank(fused, self.catalog, state, active, self.config)
            except Exception:
                ranked = fused

        ranked = backfill_popularity(ranked, self.catalog, top_k)
        recs = [asin for asin, _ in ranked[:top_k]]
        state.last_candidates = list(recs)

        ask: str | None = None
        if budget.can_afford(20):
            try:
                ask = choose_ask_attribute(self.catalog, state, ranked, self.config)
            except Exception:
                ask = None
            if ask is not None:
                if ask not in self.config.ask_attributes:
                    ask = None
                else:
                    if ask == "other":
                        state.asked.append(ask)
                    else:
                        state.mark_asked(ask)
                    self.metrics["ask_attribute_selected"][ask] += 1
        else:
            self.metrics["budget_degradations"]["skip_question"] += 1

        message = _compose_message(state, recs, ask, self.catalog)
        return payload(message, ask, recs)

    def _run_routes(
        self,
        active: list[Constraint],
        utterance: str,
        state: SessionState,
        skip_dense: bool,
    ) -> dict[str, list[tuple[str, float]]]:
        hits: dict[str, list[tuple[str, float]]] = {}
        if self.config.exact_phrase_enabled:
            try:
                hits["exact_phrase"] = self.exact.retrieve(active, self.config.K_exact)
            except Exception:
                hits["exact_phrase"] = []
            try:
                hits["intent_exact"] = self._intent_exact_hits(state, self.config.K_exact)
            except Exception:
                hits["intent_exact"] = []
        if self.config.lexical_enabled:
            try:
                hits["lexical"] = self.lexical.retrieve(active, utterance, self.config.K_lexical)
            except Exception:
                hits["lexical"] = []
        if self.config.dense_enabled and not skip_dense:
            try:
                dense_hits, qvec = self.dense.retrieve(
                    active,
                    utterance,
                    state.leaf_category,
                    self.config.K_dense,
                    cached_vec=state.last_query_vec,
                )
                hits["dense"] = dense_hits
                if qvec is not None:
                    state.last_query_vec = qvec
            except Exception:
                hits["dense"] = []
        return hits

    def _intent_exact_hits(self, state: SessionState, k: int) -> list[tuple[str, float]]:
        if k <= 0 or not state.disclosed_texts:
            return []
        scores: dict[str, float] = {}
        for text in state.disclosed_texts:
            asins = self.catalog.intent_constraint_to_asins.get(text)
            if not asins:
                continue
            if len(asins) > 50:
                weight = 0.25
            else:
                weight = 20.0 / max(len(asins), 1)
            for asin in asins:
                scores[asin] = scores.get(asin, 0.0) + weight
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]

    def _recover_empty_pool(
        self,
        fused: list[tuple[str, float]],
        active: list[Constraint],
        utterance: str,
        state: SessionState,
        skip_dense: bool,
        top_k: int,
    ) -> list[tuple[str, float]]:
        self.metrics["empty_pool_recoveries"] += 1
        remaining = list(active)
        for _ in range(3):
            if len(fused) >= top_k or not remaining:
                break
            weakest_i = min(range(len(remaining)), key=lambda i: remaining[i].confidence)
            remaining.pop(weakest_i)
            route_hits = self._run_routes(remaining, utterance, state, skip_dense)
            fused = fuse(route_hits, self.config, n_fuse=max(self.config.N_fuse, top_k))
        if len(fused) < top_k and utterance:
            lexical_only = {
                "lexical": self.lexical.retrieve([], utterance, self.config.K_lexical)
            }
            extra = fuse(lexical_only, self.config, n_fuse=top_k)
            seen = {a for a, _ in fused}
            for asin, score in extra:
                if asin not in seen:
                    fused.append((asin, score))
                    seen.add(asin)
                if len(fused) >= top_k:
                    break
        return fused

    def _degraded_response(self, session_id: str, top_k: int, reason: str) -> dict:
        state = self._sessions.get(session_id)
        seed: list[tuple[str, float]] = []
        if state and state.last_candidates:
            seed = [(a, 1.0) for a in state.last_candidates]
        filled = backfill_popularity(seed, self.catalog, top_k)
        recs = [a for a, _ in filled[:top_k]]
        if state is not None:
            state.last_candidates = list(recs)
        return payload(reason, None, recs)


def _compose_message(
    state: SessionState,
    recs: list[str],
    ask: str | None,
    catalog: CatalogStore,
) -> str:
    # Product titles belong in recommendations, not repeated in every chat line.
    if ask:
        return f"Could you share a preferred {ask}?"
    if state.slots or state.leaf_category:
        return "Here are the closest matches so far."
    return "Tell me a product type, color, or material."
