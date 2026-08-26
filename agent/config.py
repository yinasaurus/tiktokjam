"""Single configuration surface. Every number is a tunable (TDD §15)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Official enum from docs/agent_api_contract.json. Anything else is a spec miss.
ALLOWED_ASK_ATTRIBUTES: tuple[str, ...] = (
    "category",
    "material",
    "color",
    "size",
    "style",
    "brand",
    "budget",
    "feature",
    "use_case",
    "other",
)


@dataclass(frozen=True, slots=True)
class Config:
    # routes — exact_phrase_enabled is the G-2 ablation switch
    exact_phrase_enabled: bool = True
    lexical_enabled: bool = True
    dense_enabled: bool = True
    K_exact: int = 50
    K_lexical: int = 200
    K_dense: int = 200
    N_fuse: int = 50

    # fusion
    rrf_k: int = 60
    w_exact: float = 1.0
    w_lexical: float = 0.6
    w_dense: float = 0.8
    agreement_alpha: float = 0.10
    route_confidence_floor: dict[str, float] = field(
        default_factory=lambda: {
            "exact_phrase": 0.0,
            "lexical": 0.0,
            "dense": 0.0,
        }
    )

    # extraction
    semantic_fallback_threshold: int = 2
    semantic_cosine_floor: float = 0.45
    force_semantic: bool = False
    oov_token_ratio: float = 0.45
    ngram_min: int = 2
    ngram_max: int = 8

    # catalog / sparse listings (FR-22). Replace after M0 missingness measurement.
    sparse_threshold: int = 2
    leaf_category_boost: float = 0.75

    # state
    retain_superseded: bool = True
    confidence_decay: float = 0.95

    # rerank — M1 ships "heuristic"; M3 swaps in trained LTR
    rerank_mode: Literal["off", "heuristic", "ltr", "cascade"] = "heuristic"
    margin_tau_high: float = 0.35
    margin_tau_low: float = 0.10
    cross_encoder_max_candidates: int = 30
    cross_encoder_enabled: bool = False

    # question policy
    entropy_stop_s_target: int = 3
    min_information_gain: float = 0.15
    ask_attributes: tuple[str, ...] = ALLOWED_ASK_ATTRIBUTES

    # budget (FR-20)
    soft_budget_ms: int = 450
    hard_budget_ms: int = 500
    safety_margin_ms: int = 8

    # index cache
    cache_dir: str = "cache"
    encoder_dir: str = "models/encoder"
    model_id: str = "model2vec:potion-retrieval-32M"

    def route_weight(self, name: str) -> float:
        return {
            "exact_phrase": self.w_exact,
            "lexical": self.w_lexical,
            "dense": self.w_dense,
        }[name]
