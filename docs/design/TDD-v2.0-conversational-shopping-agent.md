# TDD v2.0 — Conversational Shopping Agent
### Technical Design Document · TikTok TechJam 2026, Track 4

| Field | Value |
|---|---|
| Status | **Draft v2.0** |
| Date | 26 August 2026 |
| Companion | `PRD-v2.0-conversational-shopping-agent.md` |
| Scope | Implementation design for all seven components, plus packaging, determinism, and test strategy |

> **Reading order.** PRD §6.6 establishes *why* each choice below was made. This document assumes those findings and does not re-argue them. Where a decision is still open, it appears in §19 with the measurement that resolves it.

---

## 1. Architecture

### 1.1 Runtime data flow

```
                          ┌─────────────────────────────────────┐
   respond(session_id,    │  [0] DEADLINE GUARD                 │
     user_message,   ────▶│  t0 = perf_counter()                │
     turn, top_k)         │  budget = 450ms (soft) / 500ms (hard)│
                          └──────────────┬──────────────────────┘
                                         ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  [1] CONSTRAINT EXTRACTION                          ~5-40ms  │
   │      lexical phrase match  →  (if weak) embedding fallback   │
   │      out: List[Constraint{text, attr, conf, source}]         │
   └──────────────────────────┬───────────────────────────────────┘
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  [2] DIALOG STATE MANAGER                            ~1ms    │
   │      SessionState{slots, asked, declined, category, intent}  │
   │      accumulate · typed override · confidence decay          │
   └──────────────────────────┬───────────────────────────────────┘
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  [3] MULTI-ROUTE RETRIEVAL                        ~10-30ms    │
   │   ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐    │
   │   │ exact-phrase  │ │  bm25s       │ │ dense            │    │
   │   │ inverted idx  │ │  lexical     │ │ numpy matmul     │    │
   │   │ top-K_e       │ │  top-K_b     │ │ top-K_d          │    │
   │   └───────┬───────┘ └──────┬───────┘ └────────┬─────────┘    │
   └───────────┴────────────────┴──────────────────┴──────────────┘
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  [4] FUSION — weighted RRF, skip-missing, agreement boost     │
   │      → N_fuse candidates (empty-pool recovery if < top_k)     │
   └──────────────────────────┬───────────────────────────────────┘
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  [5] RERANKER CASCADE                             ~2-150ms   │
   │      margin gate → skip │ LTR │ (opt) ONNX-int8 cross-enc     │
   └──────────────────────────┬───────────────────────────────────┘
                              ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  [6] QUESTION POLICY — entropy + stopping rule       ~2ms    │
   └──────────────────────────┬───────────────────────────────────┘
                              ▼
                    AgentResponse{recommendations[10],
                                  ask_attribute|null,
                                  message, usage}
```

### 1.2 Design invariants

These hold at every stage and are asserted in tests:

1. **Never raise.** Every stage is wrapped; failure degrades to the previous stage's output. The response path has no code path that returns `None`.
2. **Never return fewer than `min(top_k, |catalog|)` ASINs.** Backfill from a static popularity list if all else fails.
3. **Every ordering is deterministic.** Stable sort keyed on `(-score, parent_asin)`.
4. **No module-level mutable state.** All session state lives on the instance, keyed by `session_id`, and is created fresh in `reset()`.
5. **The deadline is checked between stages, never inside a tight loop.**

---

## 2. Latency and memory budget

### 2.1 Per-turn budget (target p95 ≤ 500 ms)

| Stage | Budget | Expected | Degradation if over |
|---|---|---|---|
| Deadline guard overhead | 1 ms | <1 ms | — |
| [1] Constraint extraction (lexical) | 20 ms | 5 ms | skip embedding fallback |
| [1] Embedding fallback (conditional) | 40 ms | 5–15 ms | skip entirely |
| [2] Dialog state | 5 ms | <1 ms | — |
| [3] Exact-phrase route | 20 ms | 2–5 ms | — |
| [3] bm25s route | 30 ms | 5–15 ms | — |
| [3] Dense route (query encode + matmul) | 40 ms | 10–25 ms | reuse previous turn's query vector |
| [4] Fusion | 10 ms | 1–3 ms | — |
| [5] LTR rerank | 30 ms | 2–8 ms | skip → return fused order |
| [5] Cross-encoder (opt, gated) | 200 ms | **unmeasured** | skip → LTR order |
| [6] Question policy | 20 ms | 1–3 ms | return `ask_attribute=null` |
| **Total (LTR path)** | **~180 ms** | **~35–75 ms** | |
| **Total (cross-encoder path)** | **~380 ms** | **unmeasured** | |

**The cross-encoder line is the only genuinely unknown number in this table** (PRD §6.6.7 — sources conflict by ~40×). It is therefore the only stage behind a gate. Everything else has enough headroom that the 500 ms budget is comfortable.

### 2.2 Memory budget

| Artefact | fp32 | fp16 | int8 |
|---|---|---|---|
| Dense embedding matrix (50,000 × 384) | 73.7 MB | 36.9 MB | 18.4 MB |
| Encoder weights (MiniLM-L6 class) | ~90 MB | ~45 MB | ~23 MB |
| Encoder weights (Model2Vec static) | ~8–30 MB | — | — |
| bm25s sparse index (50k docs) | ~20–60 MB | — | — |
| Exact-phrase inverted index | ~10–30 MB | — | — |
| Catalog records (normalised, in memory) | ~150–300 MB | — | — |
| **Peak RSS estimate** | **~400–600 MB** | | |

Record peak RSS at M2.5 and disclose it (NFR-7). If the grader's limit turns out to be tight, the reduction order is: fp16 embeddings → drop raw `description` text after indexing → memory-map the bm25s index.

---

## 3. Data layer

### 3.1 Catalog normalisation

Run once at build time. Produces a frozen `CatalogStore` that every route reads from.

```python
@dataclass(frozen=True, slots=True)
class Product:
    parent_asin: str          # the only scored field
    title: str                # always present in practice; '' if not
    text_blob: str            # title + features + description, cleaned
    leaf_category: str        # last element of categories, '' if absent
    category_path: tuple[str, ...]
    attr_phrases: frozenset[str]   # normalised phrases from features/details
    details: Mapping[str, str]     # parsed, lowercased keys
    price: float | None            # NEVER a string. See 3.2
    avg_rating: float
    rating_count: int
    store: str
    is_sparse: bool           # True if features+description under threshold
```

### 3.2 Defensive field parsing (FR-21)

The known failure sources, each with a required handler. **Every one of these gets a unit test asserting no exception and a sane default.**

| Field | Hazard | Handler |
|---|---|---|
| `price` | **String, with missing as the literal `"None"`**; may also be `""`, a range (`"$12.99 - $19.99"`), or carry a currency symbol | `parse_price()` → strip symbols, take the low end of a range, return `None` on `"None"`/`""`/parse failure. **Never `float(x)` directly.** |
| `details` | May arrive as a **JSON string** rather than a dict; open schema, keys vary by product | `json.loads` inside try/except; fall back to `{}`; lowercase and strip keys; coerce all values to `str` |
| `features` | List, may be empty, may contain non-strings | Coerce elements to `str`, drop empties |
| `description` | List; often retains section-header artefacts (`"Description"`, `"Feature"`, `"Package Including"`); may contain HTML entities | Join, `html.unescape`, strip a header stoplist, collapse whitespace |
| `categories` | List, may be empty or single-element | `leaf_category = categories[-1] if categories else ''` |
| `parent_asin` | Collapses colour/size/style variants — apparent near-duplicates are expected | Dedup on `parent_asin` only; do **not** dedup on title similarity |
| any | Field absent entirely (~26.5% of items lack metadata dataset-wide; measure your slice at M0) | `.get()` with typed defaults throughout; set `is_sparse` |

### 3.3 Attribute phrase extraction

The exact-phrase route indexes normalised phrases derived from `features` and `details`. Normalisation must be **identical** at index time and query time or the route silently returns nothing.

```
normalise(phrase):
    lowercase → html.unescape → strip punctuation except intra-word hyphen
    → collapse whitespace → strip a stoplist of packaging boilerplate
    → return if 2 ≤ len(tokens) ≤ 8 else drop
```

Store the normalisation function in one module, import it in both paths, and unit-test that `normalise(index_side) == normalise(query_side)` for a sample of 100 real phrases. **This single mismatch is the most likely cause of a route that appears wired up and contributes nothing.**

### 3.4 Sparse-listing fallback (FR-22)

At M0, measure the distribution of `len(features) + len(description)` across the 50k slice. Set `is_sparse` at the 10th percentile. For sparse products, the exact-phrase route has little to index; the fallback is:

- index the **title** tokenised into 2–4-grams as pseudo-attribute-phrases
- index the **full category path**, not just the leaf
- rely proportionally more on bm25s and dense, which degrade gracefully on short text

Report the sparse-subset score separately in the ablation table. A judge will find this more convincing than an aggregate.

---

## 4. Index build strategy

### 4.1 The constraint collision

Three requirements interact badly and must be resolved as one decision:

- NFR-4: index available ≤ 60 s from cold start
- NFR-2: reproducible from the submitted bundle alone
- C-9 / NFR-13: no git blob over 100 MiB

### 4.2 Decision: **build at runtime, cache to disk, commit nothing large**

```
build_index(catalog_path, cache_dir):
    key = sha256(catalog_bytes + config_hash + model_id)
    if cache_dir/{key}.npz exists:
        load embeddings from cache        # ~1s
    else:
        encode 50k docs in one batched call   # see 4.3
        atomically write cache_dir/{key}.npz
    build bm25s index                      # <1s
    build exact-phrase inverted index      # ~2-5s
```

**Why this and not a committed artefact:**
- Satisfies NFR-2 and NFR-13 unconditionally — the repo contains code and small model weights, nothing else.
- Satisfies NFR-4 on the second and subsequent runs trivially, and on the first run provided §4.3 holds.
- Survives either answer to PRD Q7. A committed 74 MB embedding matrix survives only one answer.
- The `.npz` cache is gitignored. The cache key includes the catalog hash, so a revised catalog (R7) invalidates it automatically rather than silently serving stale vectors.

### 4.3 Encoder choice — and why it is gated on a measurement

| Option | 50k encode (est.) | Query encode | Weights | torch? | Quality |
|---|---|---|---|---|---|
| **A. MiniLM-L6-v2** (384d) | ~4–40 s | 1–10 ms | ~90 MB | yes | baseline |
| **B. bge-small-en-v1.5** (384d) | similar to A | similar | ~130 MB | yes | typically > A on retrieval |
| **C. Model2Vec / potion-retrieval-32M** (static) | **<1 s** | <1 ms | ~30 MB | **no** | ~92% of A on MTEB |
| **D. A or B, exported ONNX-int8** | ~3–5× faster than A | ~3–5× faster | ~25 MB | no (onnxruntime) | <1% loss |

**Default: C (Model2Vec static).** It removes torch — the single largest, slowest-installing, most offline-fragile dependency — makes the 60 s build budget a non-issue, and shrinks the vendored weights well under the 100 MiB blob limit. The ~8% MTEB gap matters far less than it looks, because the dense route is the *robustness* route, not the precision route; precision comes from the exact-phrase route and the reranker.

**Escalate to D (ONNX-int8 MiniLM/BGE) if and only if** measured dense-route Recall@50 with C is more than 3 points below A on your held-out split. Measure this at M2, log both, and put the comparison in the ablation table — a documented "we chose the 92%-quality model because it removed a 2 GB dependency and cost us 1.4 points of recall" is a *stronger* Feasibility answer than silently using the bigger model.

**Never:** encode inside a Python loop item-by-item. Batch all 50k in one call. The difference between batched and unbatched is roughly an order of magnitude and is the usual cause of a blown build budget.

### 4.4 Prefix hazard

`bge-*` and `e5-*` families require asymmetric prefixes (`"query: "` / `"passage: "`). Omitting them **silently** degrades retrieval — no error, just worse numbers you will misattribute to the architecture. If you use B or D, wrap encoding in a single function that applies the prefix and assert on it in a test.

---

## 5. Component 1 — Constraint Extraction

### 5.1 Contract

```python
def extract(utterance: str, state: SessionState) -> list[Constraint]

@dataclass(frozen=True, slots=True)
class Constraint:
    text: str            # normalised phrase
    attribute: str|None  # one of the ten, if inferable
    confidence: float    # 0..1
    source: Literal["exact", "semantic", "category", "profile"]
    turn: int
```

### 5.2 Two-path design

**Fast path — lexical.** Slide an n-gram window (n = 2..8) over the normalised utterance; look up each window in the attribute-phrase vocabulary (a `dict[str, set[int]]` built at index time). Emit hits with `confidence = 1.0`, `source="exact"`.

**Fallback path — semantic.** Triggered when *any* of:
- lexical path yields fewer than 2 constraints, **or**
- the utterance contains tokens absent from the entire phrase vocabulary above a threshold ratio, **or**
- `config.force_semantic` is set (used for the FR-16 verification run)

Encode the utterance, take top-M nearest attribute-phrase embeddings above a cosine floor, emit with `confidence = cosine`, `source="semantic"`.

### 5.3 Why the fallback must fire on the public set too (FR-16)

A fallback that never executes during development is untested code shipped to the only run that counts. Instrument a counter: `semantic_fallback_fired` per session. Assert in the M2.5 gate that it is non-zero across the 200-session run. If it is zero, lower the trigger threshold until it fires on at least ~10% of turns, then verify the score does not *degrade* — a fallback that fires and makes things worse is worse than no fallback.

### 5.4 Ablation hook (G-2)

`config.routes.exact_phrase.enabled = False` must disable the exact-phrase route *and* the lexical extraction path, forcing everything through semantics and bm25s. The resulting TechnicalScore is the G-2 ablation floor. Wire this as a config flag, not a code edit, so it is a one-command experiment.

---

## 6. Component 2 — Dialog State Manager

### 6.1 State model

```python
@dataclass
class SessionState:
    session_id: str
    user_profile: dict
    turn: int = 0
    leaf_category: str | None = None
    intent: Literal["buying","browsing","unknown"] = "unknown"
    slots: dict[str, SlotValue] = field(default_factory=dict)   # attribute → value
    free_constraints: list[Constraint] = field(default_factory=list)  # unattributed
    asked: set[str] = field(default_factory=set)
    declined: set[str] = field(default_factory=set)
    last_candidates: list[str] = field(default_factory=list)
    last_query_vec: np.ndarray | None = None

@dataclass
class SlotValue:
    value: str
    confidence: float
    set_at_turn: int
    superseded: list[str] = field(default_factory=list)  # kept, not discarded
```

### 6.2 Override semantics (FR-8, FR-17)

Three cases, handled distinctly:

| Case | Trigger | Behaviour |
|---|---|---|
| **Accumulate** | New attribute, slot empty | Fill slot |
| **Partial override** | Existing slot gets a new value; other slots untouched | Move old value into `superseded`, set new value. **Other slots persist.** |
| **Full override** | Explicit reset signal (category change) | Clear slots, retain `leaf_category` history, keep `free_constraints` at reduced weight |

**The simulator-specific optimisation, stated honestly:** in this simulator the old and new values both derive from the same target product, so the override does not genuinely contradict — retaining the superseded value in the retrieval query is optimal. `config.override.retain_superseded = True` captures this, defaults to `True`, and is documented in the report as an environment-specific tuning choice rather than a general principle. A judge will respect the distinction; hiding it is what looks bad.

### 6.3 Confidence decay

Constraints from earlier turns decay: `weight = base_conf × decay^(current_turn − set_turn)`, `decay = 0.95` default. This is near-neutral in this simulator (nothing genuinely contradicts) but is the correct model, is cheap, and gives the question policy a reason to re-weight rather than re-ask.

### 6.4 Cross-session isolation (R9)

`reset()` must construct a **new** `SessionState` object and clear every per-session cache. Prohibited in the agent package:

- module-level mutable containers
- `@functools.lru_cache` on any function whose result depends on session state
- mutable default arguments
- class-level attributes that are written to
- an un-reseeded RNG

The M2.5 test (§16.4) catches violations by running the harness twice in different session orders and asserting identical per-session results.

---

## 7. Component 3 — Multi-Route Retrieval

### 7.1 Route A — Exact-phrase inverted index

```
phrase_to_docs: dict[str, np.ndarray]   # normalised phrase → sorted doc ids
```

Scoring: for the accumulated constraint set, intersect or count. Use **counting, not intersection** — strict intersection is what produces the empty pool in §8.3.

```
score_A(doc) = Σ_{c in constraints} weight(c) · idf(c) · 1[doc in phrase_to_docs[c.text]]
```

Add the leaf-category filter as a *boost*, not a hard filter, so a wrong category inference cannot zero out the pool.

**Properties:** highest precision, brittle to rewording, the route that gets ablated for G-2.

### 7.2 Route B — bm25s lexical

`bm25s` over `text_blob`. Build once, retain the tokeniser, query with the concatenated constraint text plus the raw utterance.

**Properties:** low precision, very robust, order-insensitive, synonym-brittle. Essentially free at this corpus size.

### 7.3 Route C — Dense

```python
scores = embeddings @ query_vec          # (50000, 384) @ (384,) → (50000,)
top = np.argpartition(-scores, K)[:K]
top = top[np.argsort(-scores[top], kind="stable")]
```

Normalise `embeddings` once at build time so the matmul is cosine. `argpartition` then a stable sort on the small slice — never a full `argsort` over 50k.

**Properties:** moderate precision, robust to rewording, the route that carries G-2.

**Query construction:** encode `f"{leaf_category}. {' '.join(constraint_texts)}. {utterance}"`. Cache the vector on `SessionState` so a turn where nothing changed can reuse it (the degradation path in §2.1).

### 7.4 Truncation sizing (FR-18)

Per-route `K` is a **measured** parameter, not an assumption. Method:

1. For each route independently, compute Recall@K of the true target over the 200 public sessions for K ∈ {10, 20, 30, 50, 100, 200, 500}.
2. Plot. Identify the plateau per route.
3. Set `K_route` at the plateau, not beyond — added distractors past the plateau can *reduce* final accuracy.
4. Set `N_fuse` (candidates entering the reranker) by the same method on fused recall.
5. Commit the plot to the repo and put it in the technical report.

Expected shape at this catalog size: exact-phrase plateaus early (it is precise), bm25s and dense need larger K. Start with `K_e=50, K_b=200, K_d=200, N_fuse=50` and correct from the data.

**The invariant this protects:** reranker recall ≤ first-stage recall. Every point lost here is unrecoverable downstream regardless of reranker quality.

---

## 8. Component 4 — Fusion

### 8.1 Weighted RRF

```
score(d) = Σ_{r ∈ routes}  w_r / (k + rank_r(d))       for r where d appears
```

- `k = 60` default. Sweep `k ∈ {10, 30, 60, 100}` at M2 — evidence suggests short result lists favour smaller `k`, and one study found `k=30` optimal.
- **Skip-missing convention.** A document absent from a route contributes nothing. Do *not* substitute `rank = len(list)+1`; each summand stays independent, which is closer to RRF's intent and avoids penalising a document for being outside one route's truncation window.
- `w_r` externally configurable (FR-10), grid-searched on a held-out split, never on the full 200.

### 8.2 Agreement boost

RRF already rewards multi-route agreement implicitly (three contributions instead of one). To make it explicit and tunable:

```
score(d) *= (1 + α · (n_routes_containing(d) − 1))     α default 0.10
```

Ablate `α ∈ {0, 0.1, 0.25}` and report. This closes the v1.1 §6.5 gap where cross-route hits were silently deduplicated rather than treated as confidence.

### 8.3 Empty-pool recovery (FR-23)

```
if len(fused) < top_k:
    1. relax the least-confident / most-recent constraint, re-run routes
    2. repeat up to 3 times
    3. if still short: backfill from bm25s over the raw utterance
    4. if still short: backfill from a static popularity list
       (rating_count desc, avg_rating desc, parent_asin asc)
    5. dedup, truncate to top_k
```

Step 4 exists so FR-2 can never be violated. It is 5 lines and it converts a spec violation into a bad-but-valid response.

### 8.4 Why not weighted score fusion

Score fusion (CombSUM/CombMNZ with min-max or z-score normalisation) can outperform RRF when scores are well calibrated. But BM25 scores, cosine similarities, and phrase-match counts live on incompatible, session-varying scales, and normalising them correctly is fragile tuning work with 72 hours on the clock. RRF needs no normalisation and no per-route calibration.

**Known RRF weakness, and the mitigation:** RRF assumes rank quality is comparable across routes — a route producing consistently poor top ranks still contributes full-strength votes. The mitigation is the `w_r` weights plus a **confidence gate**: if a route's top-1 score falls below a per-route floor, drop that route's contribution for the turn entirely. This matters specifically when the exact-phrase route returns near-garbage under paraphrased input — exactly the G-2 scenario.

---

## 9. Component 5 — Reranker Cascade

### 9.1 Three tiers, gated

```
margin = (s[0] − s[1]) / max(s[0], ε)          # on fused scores

if margin > τ_high:            # confident — the fused top-1 is almost certainly right
    return fused_order          # ~0ms
elif cross_encoder_enabled and margin < τ_low and time_remaining > 250ms:
    return cross_encode(top_30) # expensive, rare
else:
    return ltr_rerank(top_N)    # ~2-8ms, the default path
```

Margin-based cascade skipping is well supported — a normalised top-1/top-2 gap has been measured as a substantially better skip predictor than top-1 fraction or entropy, with large speedups at parity. Given that the fused top-1 is already correct on 56% of sessions before any reranking, the skip path should fire often.

**τ_high and τ_low are calibrated on a held-out split, never by intuition.** Confidence gates set by intuition are reliably miscalibrated and fire too eagerly, skipping exactly the queries the downstream stage would have fixed.

### 9.2 Tier 2 — LTR (the default, and the recommended primary)

LightGBM `LGBMRanker` (LambdaRank objective) over cheap features. Inference is microseconds; no transformer in the per-turn path.

**Features per (session_state, candidate):**

| Feature | Rationale |
|---|---|
| RRF fused score | the prior |
| per-route rank and score (×3) | lets the model learn which route to trust when |
| n_routes_containing | agreement |
| constraint_coverage = matched / total | the core signal your extraction stage produces |
| max/mean constraint confidence among matched | weights soft matches down |
| leaf_category_exact_match | binary |
| category_path_overlap | graded |
| title_token_overlap with utterance | cheap lexical prior |
| is_sparse | lets the model discount thin listings |
| log1p(rating_count), avg_rating | popularity prior — the turn-1 cold-start backstop |
| price_present, price_zscore_within_category | usable only if a price constraint exists |
| turn index | early turns are less constrained |

**Training data:** the 200 public sessions, each turn producing one positive (the target) and N_fuse−1 negatives. That is ~200 × ~2 turns × 50 ≈ 20k rows — small but adequate for a shallow LambdaRank model. **Hold out 40 sessions**, train on 160, and report both. Over-tuning to 200 sessions is R4.

**Why LTR over a cross-encoder as the default:** your pipeline already produces structured constraint-satisfaction signals that a cross-encoder would have to re-derive from raw text. The features above encode the actual task; a general-purpose semantic relevance model does not know what "constraint coverage" means. It is also ~50× faster and has no latency risk.

### 9.3 Tier 3 — cross-encoder (optional, gated, must be earned)

If adopted: `cross-encoder/ms-marco-MiniLM-L-6-v2` exported to **ONNX int8** (≈3–5× CPU speedup at <1% quality loss; note int8 is a CPU-only win and is *slower* on GPU). Cap at 30 candidates. `ms-marco-MiniLM-L-2-v2` is the ~3× faster degradation target.

**Adoption gate (NFR-8), run before any integration:**

```
benchmark: 30 candidates × 200 iterations, on the target CPU, threads pinned to 1
adopt if   p95 < 150ms
degrade    to L-2-v2 if 150ms ≤ p95 < 250ms
reject     if p95 ≥ 250ms — ship LTR only
```

Do this benchmark in **isolation, before integration**, because after integration a latency regression is indistinguishable from a quality regression in the aggregate score.

Do **not** consider `bge-reranker-v2-m3` or similar — at roughly 12 s per 1,000 candidates it exceeds the entire turn budget at 50 candidates.

### 9.4 Expected uplift

Per PRD §6.4: promoting the rank-2 and rank-3 populations to rank 1 yields **+0.039 TechnicalScore** and lands at ~0.933. Lifting the ranks 4–10 tail adds up to ~+0.014 more. Anything above that is diminishing.

---

## 10. Component 6 — Question Policy

### 10.1 Objective

Choose `ask_attribute` to maximise expected reduction in candidate-pool entropy, subject to never wasting a turn.

```
H(C) = −Σ_{d ∈ C} p(d) log p(d)          p(d) ∝ softmax(fused score)

Q* = argmin_{a ∈ A_available}  Σ_v P(v|a) · H(C | a=v)
```

where `A_available = TEN_ATTRIBUTES − state.asked − state.declined` (FR-19) and `P(v|a)` is estimated from the empirical distribution of attribute `a`'s values across the current candidate pool.

### 10.2 Stopping rule (FR-27)

```
if H(C) < log(s_target):          # mass concentrated on ≤ s_target items
    ask_attribute = None
elif expected_gain(Q*) < min_gain_threshold:
    ask_attribute = None          # no attribute discriminates → don't waste the turn
else:
    ask_attribute = Q*
```

`s_target` default 3, `min_gain_threshold` default 0.15 nats. Both configurable and swept.

**Scoring-aware bias.** Because MTTC charges misses at turn 11 and the target is already in the top 10 on 99.5% of sessions by turn ~1.6, the marginal value of asking is *low* in this environment. The policy should be biased toward `None`. Note this explicitly in the report: the information-gain machinery is correct and general, and this particular environment happens to reward using it sparingly.

### 10.3 The `"other"` question

Always asking `"other"` is optimal against this simulator (it short-circuits the disclosure filter) and indefensible in a writeup. Handle it this way: implement the genuine information-gain policy; let `"other"` be a *legal option* the policy may select when the pool is large and no specific attribute dominates — which is exactly when a real system would ask something broad. Log how often it is selected. If it is selected 100% of the time, the policy is not doing its job; investigate rather than ship it.

### 10.4 Never re-ask (FR-19)

`state.asked` and `state.declined` are both excluded. Declined attributes stay excluded permanently for the session (Boundary scenario). Test: replay all 200 sessions, assert no `ask_attribute` value repeats within any session.

---

## 11. Component 0 — Deadline Guard (FR-20)

### 11.1 Design

```python
class TurnBudget:
    def __init__(self, soft_ms=450, hard_ms=500):
        self.t0 = time.perf_counter()
    def remaining_ms(self) -> float: ...
    def can_afford(self, cost_ms: float) -> bool:
        return self.remaining_ms() > cost_ms + SAFETY_MARGIN_MS
```

Checked **between stages**, never inside a loop. Each stage declares an estimated cost; the guard decides.

### 11.2 Degradation ladder

| Remaining | Behaviour |
|---|---|
| > 250 ms | full pipeline, cross-encoder eligible |
| 100–250 ms | LTR rerank, no cross-encoder |
| 40–100 ms | skip rerank, return fused order |
| 10–40 ms | skip dense route, return exact-phrase + bm25s fused |
| < 10 ms | return `state.last_candidates`, or the static popularity list |

**Every rung returns a valid, complete response.** There is no rung that raises or returns short.

### 11.3 Why this is P0

C-8 makes a timeout a miss. A miss costs the full session — 0.50 weight on HitRate plus 0.30 on MRR plus a turn-11 MTTC charge. A degraded-but-valid response costs a few rank positions. The guard converts the former into the latter for about 40 lines of code. It is the highest ratio of score-protected to effort-spent in the entire system.

---

## 12. Determinism specification (NFR-9–NFR-11, G-5)

### 12.1 Required at process start, before numpy import

```python
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("PYTHONHASHSEED", "0")
```

Thread count changes float reduction order; non-associative addition then produces different bits. This is not theoretical — measured cases exist where 1 vs 4 threads differ while 4 vs 16 are identical. Pinning to 1 also makes latency measurements meaningful.

### 12.2 Required in every ranking path

```python
# WRONG — unstable, ties reorder across runs and platforms
order = np.argsort(-scores)

# RIGHT — stable, with an explicit deterministic tie-break
order = sorted(range(len(scores)),
               key=lambda i: (-scores[i], asins[i]))
# or, vectorised:
order = np.lexsort((asin_codes, -scores))
```

Ties are common — the exact-phrase route produces integer-valued counts, so many candidates tie exactly. Reciprocal rank and top-10 membership are both directly sensitive to tie order.

### 12.3 Prohibited

- iterating a `set` or an unordered `dict` in any path that affects output ordering
- `random` / `np.random` without a per-session seed
- any ANN index (NG-8) — approximate results vary across runs and platforms
- floating-point accumulation order that depends on dict insertion order

### 12.4 Verification

M2.5 and M6: run the full 200-session harness twice from a clean process, `diff` the `results.json`. Byte-identical or it fails.

---

## 13. Offline packaging (NFR-12–NFR-14)

### 13.1 Environment

```python
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HOME"] = str(VENDORED_MODEL_DIR)
```

### 13.2 Load from a path, never a repo id

```python
# WRONG — may attempt a metadata call even with weights cached; can hang under a firewall
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# RIGHT
model = SentenceTransformer(str(REPO_ROOT / "models" / "encoder"), local_files_only=True)
```

Vendor the **complete** model directory: `config.json`, tokenizer files, weights, and for sentence-transformers the `modules.json` and pooling config. A partially vendored directory fails at first use, not at load.

**Known hazard:** the failure mode under a firewall is often a *hang until timeout*, not an exception — which under C-8 is a miss, not a visible error. And at least one library bug has had `HF_HUB_OFFLINE=1` bypass the local cache and attempt a download anyway. Assumption is not verification.

### 13.3 Artefact sizing against C-9

| Artefact | Size | Strategy |
|---|---|---|
| Model2Vec static encoder | ~8–30 MB | **commit directly** — well under 100 MiB |
| ONNX-int8 MiniLM | ~25 MB | commit directly |
| fp32 MiniLM | ~90 MB | commits, but close to the limit — prefer int8 |
| Embedding matrix (74 MB fp32) | 74 MB | **do not commit** — gitignored runtime cache (§4.2) |
| LightGBM model | <1 MB | commit |
| Catalog | organiser-provided | do not commit |

**Avoid Git LFS entirely.** The free quota is 1–10 GiB for storage *and* bandwidth, every push of a large file re-consumes storage, and exceeding it silently blocks pushes or downloads — a failure that surfaces at submission time. If an artefact genuinely must exceed 100 MiB, use a GitHub Release asset with a SHA256 check, not LFS.

### 13.4 Dependencies

Pin exact versions. Prefer the torch-free path (§4.3 option C) — it removes the largest and most offline-fragile dependency. If torch is required, use the CPU-only wheel index explicitly so a CUDA build is never pulled.

```
numpy==<pin>
scipy==<pin>
bm25s==<pin>
lightgbm==<pin>
model2vec==<pin>        # OR onnxruntime + tokenizers if using option D
```

### 13.5 Verification (M6)

```bash
git clone <repo> /tmp/verify && cd /tmp/verify
pip install -r requirements.txt --no-index --find-links ./wheels   # or online, then:
sudo ip link set eth0 down     # or: unshare -n
python -m evaluator.run --sessions 200
```

Network **actually** disabled, not assumed. Twice, and diff the outputs.

---

## 14. Repository layout

```
repo/
├── README.md                    # overview, setup, reproduction, limitations, contributions
├── requirements.txt             # pinned
├── DISCLOSURE.md                # deliverable 5
├── docs/
│   └── design/
│       ├── PRD-v2.0-conversational-shopping-agent.md
│       └── TDD-v2.0-conversational-shopping-agent.md
├── report/
│   ├── technical_report.md      # deliverable 4
│   └── figures/
│       ├── recall_at_k.png      # FR-18
│       └── ablation_table.md
├── agent/
│   ├── __init__.py              # exports Agent — C-2
│   ├── agent.py                 # orchestration + deadline guard
│   ├── budget.py                # TurnBudget
│   ├── config.py                # ALL tunables, one dataclass
│   ├── determinism.py           # env pinning, stable sort helpers — imported first
│   ├── catalog.py               # Product, normalisation, defensive parsing
│   ├── normalise.py             # THE shared phrase normaliser (§3.3)
│   ├── extract.py               # Component 1
│   ├── state.py                 # Component 2
│   ├── routes/
│   │   ├── exact_phrase.py
│   │   ├── lexical.py           # bm25s
│   │   └── dense.py             # numpy brute force
│   ├── fusion.py                # Component 4
│   ├── rerank.py                # Component 5 cascade
│   └── question.py              # Component 6
├── models/
│   ├── encoder/                 # vendored, complete, <100MiB
│   └── ltr.txt                  # LightGBM model
├── scripts/
│   ├── build_index.py
│   ├── measure_recall_at_k.py   # FR-18
│   ├── run_ablations.py         # G-2 + route ablations
│   ├── bench_reranker.py        # NFR-8
│   └── check_determinism.py     # NFR-9
├── tests/
│   ├── test_parsing.py          # FR-21 — including the literal "None"
│   ├── test_normalise_symmetry.py  # §3.3
│   ├── test_never_raises.py     # FR-5 fault injection
│   ├── test_session_isolation.py   # R9
│   ├── test_no_repeat_ask.py    # FR-19
│   ├── test_min_results.py      # FR-2 / FR-23
│   └── test_determinism.py      # NFR-9
└── .gitignore                   # cache/, *.npz, catalog data
```

**`agent/` imports nothing from `evaluator/`.** Not once, not for a type, not for a constant. A judge grepping for that import is a five-second check and it is the difference between "characterised the environment" and "fitted the simulator."

---

## 15. Configuration surface

One dataclass, serialised to the report. Every number below is a tunable that was measured, not guessed.

```python
@dataclass
class Config:
    # routes
    exact_phrase_enabled: bool = True      # G-2 ablation switch
    lexical_enabled: bool = True
    dense_enabled: bool = True
    K_exact: int = 50                      # FR-18 — set from recall curve
    K_lexical: int = 200
    K_dense: int = 200
    N_fuse: int = 50

    # fusion
    rrf_k: int = 60                        # sweep {10,30,60,100}
    w_exact: float = 1.0
    w_lexical: float = 0.6
    w_dense: float = 0.8
    agreement_alpha: float = 0.10
    route_confidence_floor: dict = ...     # drop a route producing garbage

    # extraction
    semantic_fallback_threshold: int = 2
    semantic_cosine_floor: float = 0.45
    force_semantic: bool = False           # FR-16 verification

    # state
    retain_superseded: bool = True         # §6.2 — environment-specific, documented
    confidence_decay: float = 0.95

    # rerank
    rerank_mode: Literal["off","ltr","cascade"] = "ltr"
    margin_tau_high: float = 0.35          # calibrated, not guessed
    margin_tau_low: float = 0.10
    cross_encoder_max_candidates: int = 30

    # question policy
    entropy_stop_s_target: int = 3
    min_information_gain: float = 0.15

    # budget
    soft_budget_ms: int = 450
    hard_budget_ms: int = 500
```

---

## 16. Test plan

### 16.1 Unit (run continuously)

| Test | Asserts |
|---|---|
| `test_parsing` | `price="None"`, `""`, `"$12.99 - $19.99"`, absent → no exception, correct `None`/float |
| `test_parsing` | `details` as JSON string, as dict, as `None` → all yield a dict |
| `test_normalise_symmetry` | `normalise(index_phrase) == normalise(query_phrase)` on 100 real samples |
| `test_min_results` | over-constrained state still returns `top_k` ASINs |
| `test_never_raises` | each stage monkeypatched to raise → response still valid |

### 16.2 Property

- For any random constraint set, `len(recommendations) == min(top_k, catalog_size)` and all are unique and catalog-resident.
- Adding a *true* constraint never worsens the target's rank by more than a tolerance (FR-7).

### 16.3 Latency (NFR-4, NFR-8)

- `bench_reranker.py` in isolation, threads pinned, p50/p95/p99 over 200 iterations, **before** integration.
- Full-harness per-turn latency histogram; assert p95 < 500 ms and max < hard budget.

### 16.4 Harness-scale (the M2.5 gate)

| Test | Method | Pass condition |
|---|---|---|
| Cross-session isolation | Run 200 sessions in order, then in reverse order | Per-session results identical |
| Determinism | Two clean runs, same order | `results.json` byte-identical |
| No repeat asks | Replay all 200, collect `ask_attribute` per session | No value repeats within a session |
| Fusion truncation | Recall@K curve per route at ≥3 sizes | Plateau identified and documented |
| Empty pool | Inject an over-constrained state | Returns `top_k`, no exception |

### 16.5 Ablation matrix (FR-10, M4 deliverable)

Run each and record TechnicalScore, per-scenario breakdown, and p95 latency:

| Configuration | Purpose |
|---|---|
| Full system | headline |
| **− exact-phrase route** | **G-2 ablation floor — the headline robustness number** |
| − dense route | shows dense is load-bearing, not decorative |
| − lexical route | route contribution |
| − reranker (`rerank_mode=off`) | isolates the +0.039 |
| − question policy (always `null`) | isolates policy contribution |
| − agreement boost (`α=0`) | isolates §8.2 |
| Static encoder vs ONNX MiniLM | §4.3 decision evidence |
| Paraphrased input (secondary) | cross-check on the ablation floor |
| Per-scenario × all above | R4 — aggregate hides scenario-level regressions |

**Report negative results.** "We tried `user_profile` weighting (FR-14) and it produced no measurable lift, so we removed it" is a stronger Technical Execution and Innovation signal than silently dropping it.

---

## 17. Failure-mode matrix

| Failure | Detection | Blast radius | Handler |
|---|---|---|---|
| `float("None")` on price | unit test | **whole harness crashes** | §3.2 `parse_price` |
| Phrase normaliser mismatch | `test_normalise_symmetry` | exact-phrase route silently returns nothing | §3.3 shared module |
| Fusion truncation too small | recall@k curve | HitRate silently capped | FR-18 sizing |
| Empty candidate pool | property test | FR-2 spec violation | §8.3 recovery ladder |
| Cross-session state leak | reverse-order run | subset of sessions corrupted, invisibly | §6.4 prohibitions |
| Unstable argsort | two-run diff | score irreproducible; judge cannot verify | §12.2 stable sort |
| BLAS thread variance | two-run diff on differing thread counts | same | §12.1 pinning |
| Cross-encoder over budget | isolated benchmark | timeout → miss (C-8) | §9.3 gate + §11 ladder |
| Model load hangs under firewall | M6 network-down run | **entire submission scores zero** | §13.2 local path + verification |
| Blob >100 MiB | `git push` fails | submission blocked at deadline | §13.3 sizing decision at M0 |
| Semantic fallback never fires | instrumentation counter | untested code ships to the run that counts | FR-16 threshold tuning |
| Over-fit to 200 public sessions | held-out split | private score collapses | 40-session holdout, per-scenario tracking |

---

## 18. Instrumentation

Log per turn, aggregate per run, put the aggregates in the report:

```
turn_latency_ms · stage_latency_ms{stage} · n_constraints_extracted
semantic_fallback_fired · route_hit_counts{route} · n_routes_agreeing_top1
fused_pool_size · margin · rerank_tier_used · ask_attribute_selected
entropy_before · entropy_after · empty_pool_recoveries · budget_degradations{rung}
```

`budget_degradations` is the one to watch: if it is non-zero on the public set at 40 s total runtime, it will be much worse on the grader's machine.

---

## 19. Open technical decisions

Each has a **measurement that resolves it** and a **default if the measurement is not done**.

| # | Decision | Resolved by | Default |
|---|---|---|---|
| D1 | Static encoder vs ONNX-int8 MiniLM | Dense-route Recall@50 gap on held-out split; escalate if >3 pts | **Static (Model2Vec)** — removes torch |
| D2 | Cross-encoder in the cascade at all | `bench_reranker.py` p95 on the target CPU | **No** — LTR only |
| D3 | `rrf_k` value | Sweep {10, 30, 60, 100} at M2 | **60** |
| D4 | Per-route `K` and `N_fuse` | Recall@k curves (FR-18) | K_e=50, K_b=200, K_d=200, N_fuse=50 |
| D5 | `retain_superseded` | Override-scenario MRR with both settings | **True**, documented as environment-specific |
| D6 | Dual-track Buying/Browsing routing (FR-13) | Per-scenario ablation vs unrouted control | Ship unrouted if no measured lift |
| D7 | `user_profile` weighting (FR-14) | Correlation check at M0; lift measurement at M4 | Drop it and **report the negative result** |
| D8 | Committed embedding artefact vs runtime build | PRD Q7 at the 28 Aug webinar | **Runtime build + gitignored cache** — survives either answer |
| D9 | `s_target` / `min_information_gain` | Sweep against MTTC and MRR jointly | 3 / 0.15 nats |
| D10 | Margin thresholds τ_high, τ_low | Calibrate on held-out split — **never by intuition** | 0.35 / 0.10 |

---

## 20. Build order

Mirrors PRD §9 milestones. Each row is independently testable; each leaves the system in a shippable state.

| Order | Build | Milestone | Unblocks |
|---|---|---|---|
| 1 | `determinism.py`, `config.py`, `catalog.py` + defensive parsing | M0/M1 | everything |
| 2 | `normalise.py` + `routes/exact_phrase.py` + `extract.py` (lexical) + `state.py` | M1 | **first submittable bundle** |
| 3 | `budget.py` + degradation ladder | M1 | C-8 protection — do this early, it is cheap |
| 4 | `routes/lexical.py` (bm25s) | M2 | robustness |
| 5 | `routes/dense.py` + encoder + build cache | M2 | **G-2 ablation floor** |
| 6 | `fusion.py` (weighted RRF + agreement + empty-pool recovery) | M2 | — |
| 7 | `measure_recall_at_k.py` → set truncation | M2.5 | recall ceiling removed |
| 8 | Isolation, determinism, repeat-ask tests | **M2.5 gate** | **M3 may not begin until these pass** |
| 9 | LTR feature extraction + training + `rerank.py` | M3 | +0.039 |
| 10 | `bench_reranker.py` → D2 decision | M3 | cross-encoder or not |
| 11 | `question.py` entropy policy + stopping rule | M4 | defensibility |
| 12 | `run_ablations.py` → full matrix | M4 | the report's evidence base |
| 13 | README, report, video, Devpost, disclosure | M5 | **30% of the grade** |
| 14 | Clean-checkout + network-down + two-run verification | M6 | NFR-1/2/9/13 |

---

## Appendix — Numbers to verify rather than trust

| Figure | Source confidence | Action |
|---|---|---|
| CPU cross-encoder latency at 30–50 candidates | **Low** — sources differ by ~40× | `bench_reranker.py` on the target CPU before adoption (D2) |
| 50k encode time for the chosen encoder | Medium | Time it at M0; it decides D1 and D8 |
| Per-field missingness on the 50k slice | Low for this slice | Measure at M0; the ~26.5% figure is dataset-wide, not yours |
| Peak RSS | Unmeasured | Record at M2.5 (NFR-7) |
| Recall@K plateau per route | Unmeasured | FR-18 curves at M2.5 |
| Grader CPU/memory/timeout limits | Unknown | PRD Q3 at the webinar; design for the worst case regardless |
| Whether MRR uses first-hit or best rank | Answerable now | Read the evaluator at M0 (PRD A3) |
