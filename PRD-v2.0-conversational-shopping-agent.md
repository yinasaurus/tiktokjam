# PRD v2.0 — Conversational Shopping Agent
### TikTok TechJam 2026, Track 4 — Shopping Copilot: AI Conversational Search and Recommendations

| Field | Value |
|---|---|
| Document | Product Requirements — Track 4 submission |
| Owner | *(fill in)* |
| Team size | *(fill in — solo permitted, max 5)* |
| Status | **Draft v2.0** — rebuilt against external evidence; supersedes v1.1 |
| Date | 26 August 2026 |
| Build window | **29 Aug 12:00 → 1 Sep 12:00 (72h)** — *verify against official Info Document* |
| Companion doc | `TDD-v2.0-conversational-shopping-agent.md` |

---

## Changelog from v1.1

v1.1 was internally coherent but rested on several assumptions that external evidence now contradicts or sharpens. This revision is **not** a strategy change — the five-component architecture stands. It corrects arithmetic, replaces one unfalsifiable gate, and adds the requirement classes v1.1 had no coverage for.

| # | Change | Why |
|---|---|---|
| 1 | **§2 rubric arithmetic corrected: 55% → 65%** | 20+20+15+10 = 65. v1.0 typo carried into v1.1. |
| 2 | **§6.4 reranking uplift restated: +0.091 → +0.039** | +0.091 is the *perfect-reranking* ceiling. FR-11's own 80% target yields ≈ +0.039. Derivation in §6.4. |
| 3 | **G-2 gate replaced: self-authored paraphrases → route ablation** | A robustness score measured against paraphrases you wrote yourself is circular. Ablation is unfakeable. §6.6.1. |
| 4 | **New P0: per-turn deadline guard (FR-20)** | C-8 counts a timeout as a miss. v1.1 had NFR-8 (*benchmark* latency) but nothing that *survives* a breach. |
| 5 | **New requirement class: data quality (FR-21–FR-23)** | `price` ships as a **string** with missing encoded as the literal `"None"`; `details` is open-schema. v1.1 assumed clean fields. |
| 6 | **New requirement class: determinism (NFR-9–NFR-11)** | BLAS thread count changes float reduction order; numpy's default argsort is unstable. Both silently corrupt rank order. |
| 7 | **New requirement class: offline packaging (NFR-12–NFR-14)** | GitHub hard-blocks blobs >100 MiB. Embedding matrix at fp32 is ~74 MB, model weights on top. NFR-2 and NFR-1 collide unless designed. |
| 8 | **New goal G-6 + FR-24–FR-26: Impact & Relevance** | 20% of the grade had **zero** mapped requirements in v1.0 and v1.1. |
| 9 | **Q1/Q5 promoted, Q-new added; three v1.1 questions deleted** | Several "open questions" are answerable by reading the shipped evaluator in 15 minutes, not by waiting for a webinar. |
| 10 | **§9 milestones anchored to the real 72h window** | v1.1 left durations relative. They are now absolute, with a hard code freeze. |
| 11 | **NFR-4 index-build budget re-scoped** | Runtime encoding of 50k docs is feasible but tight; the build strategy is now an explicit decision with a documented fallback. |

---

## 1. Summary

Build an offline, multi-turn shopping agent that identifies a hidden target product from a frozen 50,000-item Amazon clothing catalog within a hard limit of 10 conversational turns, ranking it as highly and as early as possible.

The winning system is not the one that scores highest against the local simulator. It is the one that scores highly, **survives a customer who does not speak in the simulator's sentence templates**, **survives the grader's machine**, and **is packaged so a judge can reproduce it**. v1.1 secured the first of those. v2.0 secures the other two.

---

## 2. Context

The organiser ships a participant kit containing a weak BM25 starter agent, a deterministic local evaluator, 200 labelled public sessions, and the frozen catalog. 800 additional sessions are held privately for final scoring, drawn from the same catalog with separate users and target products.

### 2.1 Judging rubric

| Criterion | Weight | Covered by |
|---|---|---|
| Technical Execution | 35% | TechnicalScore + code quality + §8.1/§8.2 |
| Innovation & Problem Insight | 20% | §6 characterisation, §10.1 writeup |
| Impact & Relevance | 20% | **G-6, FR-24–FR-26 (new in v2.0)** |
| Feasibility & Practicality | 15% | NFR-1–NFR-14, cost/latency disclosure |
| Presentation & Communication | 10% | Deliverables §10, M5 |

**TechnicalScore informs Technical Execution only. The other 65% rewards architecture, insight, real-world plausibility, and communication.**

Two facts sharpen this. First, the 2026 judging panel includes engineers from TikTok's Global E-Commerce Search org — people who will read the retrieval code and recognise a simulator fit on sight. Second, `Impact & Relevance` is explicitly scored on value "beyond solving for the hackathon prompt alone." An agent that scores 0.95 and has no story about a real shopper loses more points than one that scores 0.93 and does.

**Corollary that governs §9:** M5 (packaging) is worth more of the final grade than M3 (precision). The schedule reflects that.

---

## 3. Goals

| ID | Goal | Measure |
|---|---|---|
| G-1 | TechnicalScore ≥ **0.93** on the public set | *(raised from 0.85 — the measured floor is already 0.894)* |
| G-2 | **Ablation floor ≥ 0.70**: with the exact-phrase route disabled, TechnicalScore stays ≥ 0.70 | Replaces v1.1's paraphrase-gap gate. See §6.6.1 |
| G-3 | Run fully offline with zero external API dependency at scoring time | Full 200-session run with egress blocked |
| G-4 | Architecture a judge recognises as a real retrieval system, not a simulator fit | No evaluator imports in agent code; three genuinely independent routes |
| G-5 | **Bit-identical reproducibility** across runs on the same machine | Two consecutive clean runs produce identical `results.json` |
| G-6 | **(new)** A defensible answer to "who is this for and why does it matter" | §10.1 impact section + demo framing |
| G-7 | Ship all five deliverables (§10) with ≥ 8h of slack before deadline | Code freeze at H+64 |

### 3.1 Non-goals

| ID | Explicitly out of scope |
|---|---|
| NG-1 | Any user interface — scoring is headless API only; a walkthrough video is accepted |
| NG-2 | Training or fine-tuning a foundation model — prohibited by the rules |
| NG-3 | External vector database infrastructure — must run in-memory |
| NG-4 | Multimodal processing — text catalogs and text dialog only |
| NG-5 | Spelling correction, typo handling, ASR noise — inputs are pre-cleaned |
| NG-6 | Multi-user concurrency — sessions are isolated single-user |
| NG-7 | Catalog mutation or mock ASIN injection — strictly forbidden |
| NG-8 | **(new)** Approximate nearest-neighbour indexing (HNSW/IVF/Annoy) — see §6.6.2; brute force is faster, exact, and deterministic at 50k |
| NG-9 | **(new)** Neural conversational query rewriting — see §6.6.4; structured slot accumulation is more controllable and drift-free |

---

## 4. Success metrics

- **HitRate@10** — fraction of sessions where the target appears in the scored top 10.
- **MRR** — mean reciprocal rank; a miss contributes 0.
- **MTTC** — mean first-hit turn; a miss is charged as turn 11.
- Only exact `parent_asin` equality counts as a hit.

```
TechnicalScore = 0.50 × HitRate@10 + 0.30 × MRR + 0.20 × Efficiency
Efficiency     = clip((11 − MTTC) / 10, 0, 1)
```

### 4.1 Targets (revised)

| Metric | BM25 baseline | Measured floor | **v2.0 target** | Ceiling |
|---|---|---|---|---|
| HitRate@10 | 0.125 | 0.995 | ≥ 0.99 | 1.000 |
| MRR | 0.068 | 0.6953 | **≥ 0.826** | 1.000 |
| MTTC | 9.81 | 1.595 | ≤ 1.60 | ~1.375 |
| TechnicalScore | 0.1067 | 0.89418 | **≥ 0.933** | ~0.9925 |
| Ablation floor (§6.6.1) | n/a | *unmeasured* | **≥ 0.70** | — |
| Rank-1 share | — | 56% | ≥ 79% | 100% |

The ceiling is not 1.0 because Intent Override sessions cannot convert before the override fires on turn 3 or 4, pinning their MTTC floor at roughly 3.5.

**Note on MTTC:** reranking *within* the top 10 does not move MTTC at all — MTTC is the first turn the target enters the top 10, and HitRate@10 is already 0.995. Efficiency is therefore effectively fixed at 0.9405 unless HitRate or first-hit turn changes. All remaining headroom is in MRR.

---

## 5. Hard constraints

| ID | Constraint | Source |
|---|---|---|
| C-1 | Maximum 10 turns per session; exceeding forces termination and zero score | Competition limits |
| C-2 | Agent must export `Agent` with `reset(session_id, user_profile)` and `respond(session_id, user_message, turn, top_k)` | API contract |
| C-3 | `ask_attribute` must be one of the ten allowed values or `null` | API contract |
| C-4 | `recommendations` ordered best-to-worst; only first 10 valid unique ASINs scored | Output rules |
| C-5 | Must run under CPU, memory, timeout and possibly disabled network restrictions | Submission rules |
| C-6 | No API keys committed; credentials via environment variables only | Model policy |
| C-7 | Must not modify evaluator files or depend on undeclared external services | Submission rules |
| C-8 | Exceptions, invalid output, and timeouts may count as a miss | Spec |
| **C-9** | **(new)** No single git blob may exceed 100 MiB; browser upload cap 25 MB; free Git LFS quota is 1–10 GiB storage *and* bandwidth | GitHub platform limits |
| **C-10** | **(new)** No external vector DB *and* no ANN index — brute-force exact search only | NG-3 + NG-8 |

C-5 remains the constraint most teams underestimate. C-9 is the new one most teams will discover at 3am on submission night.

---

## 6. Research findings

### 6.1 The simulated customer is deterministic and invertible

*(unchanged from v1.1)* The hidden intent card is generated by a public function in `evaluator/local_evaluator.py` from the target product's own metadata. Participants hold both that function and the full catalog. Three exploitable properties:

- `ask_attribute: "other"` short-circuits the disclosure filter, returning two undisclosed constraints per turn regardless of type. Unrecognised attribute strings also coerce to `"other"`.
- Disclosed constraints are verbatim product strings lifted from `features` and `details`.
- The opening utterance leaks the target's leaf category, plus the first hard constraint on Buying sessions.

**Measured:** 87.5% of catalog products are uniquely identified by leaf category plus their four derived constraints.

### 6.2 Consequence

A pure lexical matcher exploiting this scores 0.8942 against 0.1067 for the BM25 starter — 8.4×, with zero tokens and no LLM.

### 6.3 Why that result is a trap

| Agent | Clean | Paraphrased | Gap |
|---|---|---|---|
| BM25 starter | 0.1067 | 0.1043 | 2% |
| Lexical matcher | 0.8942 | 0.1972 | **78%** |

The spec states that organiser-added paraphrasing "cannot decide correctness." That sentence only needed writing if paraphrasing is under consideration. **Treat the private 800 as paraphrased.**

### 6.4 Where the remaining points actually are — corrected

The lexical matcher hits on 99.5% of sessions but ranks the target #1 on only 56%. v1.1 valued closing this at **+0.091**. That figure is the *perfect-reranking* ceiling, not the plan. Derived from the Appendix A rank distribution (r1=112, r2=27, r3=19, r4–10=41, miss=1):

| Scenario | Rank-1 share | MRR | TechnicalScore | Δ |
|---|---|---|---|---|
| Current (lexical matcher) | 56% | 0.6953 | 0.8942 | — |
| **All r2 + r3 promoted to r1** | **79%** | 0.826 | **0.9335** | **+0.039** |
| Above, plus r4–10 tail lifted to avg rank 2.5 | 79% | 0.872 | 0.947 | +0.053 |
| Perfect (every hit at rank 1) | 99.5% | 0.995 | 0.9841 | +0.090 |

**Reading:** FR-11's existing 80% rank-1 target is well calibrated — it lands at ~0.933, exactly G-1. But the *headline number* in the writeup must be +0.039, not +0.091. A judge from an e-commerce search team will do this arithmetic. Getting caught inflating your own uplift costs more Innovation points than the uplift was worth.

### 6.5 Edge cases and silent failure modes

*(carried from v1.1 §6.5, condensed — none of these throw; all either cap the ceiling or corrupt a subset of sessions)*

**Retrieval/fusion:** fusion truncation ceiling (target dropped before the reranker sees it); empty or near-empty candidate pool violating FR-2; cross-route agreement treated as dedup rather than confidence.
**Dialog state:** question-policy looping (re-asking asked or declined attributes); partial vs full override; turn-1 cold start if the private set's opening utterance is less generous than §6.1's leak.
**Performance:** reranker latency vs the 500 ms budget; cross-session state leakage in a sequential single-process harness.
**Data:** constraint extraction tuned on well-populated `features`/`details` failing silently on thin listings.
**Non-technical:** real brand names in `title`/`store` appearing in the demo video under the no-trademarks clause.

### 6.6 External evidence findings *(new in v2.0)*

These come from research outside the participant kit and each one changes a decision.

#### 6.6.1 Self-authored paraphrase sets systematically overstate robustness

A paraphrase set you generate inherits your own lexical and semantic priors — you paraphrase in ways your extractor already handles. If the organiser's paraphrasing substitutes *attribute values* rather than injecting filler and dropping tokens, a self-measured 15% gap could mask a real 60% gap.

**Decision:** G-2's gate becomes **route ablation**. Disable the exact-phrase route entirely and re-score. That number is your true floor, it cannot be gamed, it is a one-line config change, and it is a far better headline for the writeup ("with our brittle route removed, we still score X") than a gap measured against your own imagination. Keep a paraphrase set as a *secondary* signal only, and generate it by a mechanism different from your extractor.

#### 6.6.2 At 50k vectors, brute force beats ANN on every axis that matters here

A normalised `embeddings @ query` matmul over 50,000 × 384 floats is a single-digit-millisecond exact search. HNSW/IVF's large speedups only materialise at tens of millions of vectors; at 50k they add build time (eating the 60 s budget), memory, recall loss, and — critically — **run-to-run and cross-platform nondeterminism**, which breaks G-5.

**Decision:** NG-8. One numpy float32 array *is* the index. Memory: 50,000 × 384 × 4 B ≈ **73.7 MB** (fp16 ≈ 37 MB, int8 ≈ 18 MB).

#### 6.6.3 BM25 library choice is a 100–500× decision

`rank_bm25` is 100–500× slower than `bm25s` on equivalent workloads at equal accuracy; one measured comparison showed 17 s vs 0.05 s for the same query set. Pyserini and Elasticsearch are faster but require a JVM, which breaks pinned-wheel offline install.

**Decision:** `bm25s` (numpy + scipy only). Not negotiable — `rank_bm25` alone could put NFR-6 out of reach.

#### 6.6.4 Structured slot accumulation beats neural query rewriting for this task

Conversational query rewriters "often fail to find omitted information or detect topic shifts in longer conversations" and introduce topic drift. History-accumulation strategies improve monotonically as conversations progress; a no-history baseline collapses ~31% by turn 2.

**Decision:** NG-9. Explicit slot state with typed override semantics. More controllable, drift-free, debuggable, and easier to explain to a judge.

#### 6.6.5 Hybrid retrieval degrades least under distribution shift

Every study reviewed points the same direction: dense retrievers degrade notably under paraphrase; BM25 is order-robust but synonym-brittle; **hybrid mitigates both**. BEIR nDCG@10 rose from 43.42 (BM25 alone) to 52.59 (hybrid) in one comparison. This is the evidentiary backing for Component 3 and it belongs in the writeup.

#### 6.6.6 Reranking cannot recover what retrieval dropped

Reranker recall is upper-bounded by first-stage Recall@k. Past a point, *more* candidates hurts — added distractors can pull accuracy below retrieval-alone. There is no universal correct truncation value.

**Decision:** FR-18 stands, with the method specified: plot recall@k per route, set truncation at the plateau, document the curve.

#### 6.6.7 CPU cross-encoder latency is a genuine budget risk

Evidence is mixed and hardware-dependent: one report puts `ms-marco-MiniLM-L-6-v2` at ~50 ms for 100 pairs on CPU; another observed 2–2.5 s for 1,000. `bge-reranker-v2-m3` is ~12 s per 1,000 — over budget at 50 candidates on its own. int8 quantisation gives ~3–5× on CPU at <1% quality loss (and is a **CPU-only** win — int8 is slower on GPU).

**Decision:** the reranker becomes a *cascade*, not a fixed stage. Feature-based LTR is the default path; a cross-encoder is opt-in, capped at ~30–50 candidates, ONNX-int8, and gated behind a top-1 score margin. Margin-based cascade skipping has been measured at up to 18.8× speedup at parity. Full design in the TDD.

#### 6.6.8 Two data-quality facts that will crash a naive parser

- **`price` ships as a string, with missing values encoded as the literal string `"None"`** — despite documentation typing it as float. Any `float(price)` will raise or mis-sort.
- **`details` is an open-schema dict, often delivered as a JSON string**, with keys varying wildly by product.

Additionally, ~26.5% of items lack metadata dataset-wide (the crawl is user-centric), `parent_asin` collapses colour/size/style variants, and `description` frequently retains section-header artefacts ("Description", "Feature", "Package Including").

**Decision:** FR-21–FR-23, plus an M0 task to measure actual per-field missingness on *your* 50k slice rather than trusting the dataset-wide figure.

#### 6.6.9 Determinism has two non-obvious failure sources

- **BLAS thread count changes float reduction order.** Non-associative addition means different thread counts give different bits. One study found 1 vs 4 threads differed while 4 vs 16 were identical.
- **numpy's default argsort is unstable.** Equal scores reorder across runs and platforms. Reciprocal rank and top-10 membership are directly sensitive to tie order.

**Decision:** NFR-9–NFR-11. Pin threads to 1, stable-sort with a `parent_asin` lexicographic tie-break, fix `PYTHONHASHSEED`, never iterate a `set` in a ranking path.

#### 6.6.10 Offline model loading fails in ways that hang rather than error

Without `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`, transformers in a firewalled environment can hang until timeout rather than failing fast. Tokenizer/config lookups still attempt metadata calls even when weights are cached. At least one library bug had `HF_HUB_OFFLINE=1` *bypass* the local cache and attempt a download.

**Decision:** NFR-12 — vendor the full model directory and load from an **explicit local path, never a repo id**. Verify with the network physically disabled, not merely assumed.

---

## 7. Architecture

Six components (five from v1.1, plus the deadline guard promoted to first-class). Full design in the companion TDD.

```
customer turn
  → [0] Deadline Guard        ── per-turn wall-clock budget, degrade don't die
  → [1] Constraint Extraction ── lexical fast path + embedding fallback
  → [2] Dialog State Manager  ── slot accumulation, typed override, decline tracking
  → [3] Multi-Route Retrieval ── exact-phrase ∥ bm25s ∥ dense (brute-force numpy)
  → [4] Fusion                ── weighted RRF, skip-missing, agreement boost
  → [5] Reranker Cascade      ── margin gate → LTR → (optional) ONNX-int8 cross-encoder
  → [6] Question Policy       ── entropy-driven, with a stopping rule
  → response
```

| Component | Maps to problem-statement pillar | Owns |
|---|---|---|
| 0 — Deadline Guard | Feasibility | C-8 survival |
| 1 — Constraint Extraction | NL Understanding | G-2 ablation floor |
| 2 — Dialog State | Multi-turn Dialog | FR-7, FR-8, FR-17 |
| 3 — Multi-Route Retrieval | Hybrid Retrieval | HitRate@10 |
| 4 — Fusion | Hybrid Retrieval | Recall preservation |
| 5 — Reranker Cascade | LLM Semantic Ranking | MRR (+0.039) |
| 6 — Question Policy | Clarification Strategy | Defensibility, MTTC |

---

## 8. Requirements

**Priority:** P0 = required to submit · P1 = required to compete · P2 = differentiator

### 8.1 Functional

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| FR-1 | P0 | Conform to the `Agent` interface | Runs unmodified in the official harness; no exceptions across 200 sessions |
| FR-2 | P0 | Return valid, deduplicated, catalog-resident ASINs ordered best-to-worst | Zero invalid IDs in `results.json` |
| FR-3 | P0 | Emit recommendations on every turn, including turns where a question is asked | Session can convert on turn 1 |
| FR-4 | P0 | Report non-negative usage token counts | Present in every response |
| FR-5 | P0 | Never raise; degrade to best-effort ranking on internal failure | Fault injection produces a valid response |
| **FR-20** | **P0** | **Per-turn wall-clock deadline guard with staged degradation** | Injected 10× slowdown in any stage still returns a valid response inside budget; no timeout-induced miss |
| **FR-21** | **P0** | **Defensive catalog field parsing** | `price="None"`, empty strings, JSON-string `details`, and missing fields all parse without exception; unit-tested against the literal `"None"` sentinel |
| FR-6 | P1 | Extract constraint phrases without relying on fixed templates | **Ablation floor ≥ 0.70 (G-2)** |
| FR-7 | P1 | Maintain cross-turn constraint state | Accumulated constraints monotonically improve rank |
| FR-8 | P1 | Handle Intent Override without discarding still-valid signal | Override scenario MRR ≥ 0.90 |
| FR-9 | P1 | Handle Boundary sessions where the customer declines to answer | Boundary HitRate ≥ 0.95; no wasted repeat asks |
| FR-10 | P1 | Fuse ≥ 3 retrieval routes with tunable weights | Weights externally configurable; per-route ablation recorded |
| FR-11 | P1 | Rerank top-N candidates before returning | Rank-1 share ≥ 79% (from 56%) → TechnicalScore ≥ 0.933 |
| FR-16 | P1 | Exercise the embedding-fallback path on the public 200, not held in reserve | Fallback fires and is verified non-decorative; ablation logged pre-submission |
| FR-17 | P1 | Support partial override (some slots persist, others change) | Synthetic partial-override case retains unrelated prior slots |
| FR-18 | P1 | Size and document per-route fusion truncation | Recall@k curve plotted per route at ≥3 sizes; plateau identified |
| FR-19 | P1 | Question Policy excludes attributes already asked or declined | No repeated `ask_attribute` within a session in replay test |
| **FR-22** | **P1** | **Graceful degradation on sparse listings** | Title/category-only fallback path; measured on the thin-listing subset identified in M0 |
| **FR-23** | **P1** | **Empty-pool recovery by constraint relaxation** | When the pool falls below `top_k`, relax the least-confident constraint and backfill; never return <`top_k` when the catalog can supply them |
| **FR-27** | **P1** | **Ask-vs-recommend stopping rule** | Policy asks only when expected entropy reduction exceeds the value of returning now; demonstrably stops asking as the pool converges |
| FR-12 | P2 | Select `ask_attribute` by expected information gain | Policy demonstrably varies attribute by pool size |
| FR-13 | P2 | Route Buying vs Browsing intent to different retrieval strategies | Per-scenario metrics improve over unrouted control |
| FR-14 | P2 | Use the anonymised `user_profile` for preference weighting | Measurable lift attributable to profile signal — **or a documented negative result** |
| FR-15 | P2 | Emit human-readable rationale in `message` | Reads naturally in the demo video |
| **FR-24** | **P2** | **Cost and token accounting per session** | Reported in the technical report; supports the zero-marginal-cost claim |
| **FR-25** | **P2** | **A named target user and use case in the writeup** | One paragraph a judge could repeat back |
| **FR-26** | **P2** | **A stated generalisation path beyond the frozen catalog** | Explains what changes for a live catalog, cold-start items, and multilingual input |

### 8.2 Non-functional

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| NFR-1 | P0 | Operate with network disabled | Full run completes with egress blocked (C-5) |
| NFR-2 | P0 | Reproducible from the submitted bundle alone | Clean-checkout run reproduces the reported score |
| NFR-3 | P0 | No secrets in the repository | Secret scan clean |
| **NFR-9** | **P0** | **Deterministic ranking** | Two consecutive clean runs produce byte-identical `results.json` |
| **NFR-12** | **P0** | **Offline model loading verified, not assumed** | Model loads from an explicit local path with `HF_HUB_OFFLINE=1`; verified with network physically disabled |
| **NFR-13** | **P0** | **All artefacts within platform limits (C-9)** | No blob >100 MiB; total repo size documented; LFS avoided or quota-checked |
| NFR-4 | P1 | Index available ≤ 60 s from cold start; per-turn p95 ≤ 500 ms | Measured and disclosed; strategy documented (§6.6.7, TDD §4) |
| NFR-5 | P1 | In-memory only; no external DB service, no ANN index | No service dependency in the manifest |
| NFR-6 | P1 | Full 200-session evaluation ≤ 5 min | Preserves the iteration loop (currently 40 s) |
| NFR-8 | P1 | Reranker latency benchmarked in isolation before adoption | Per-turn latency with reranker enabled logged across all 200 sessions |
| **NFR-10** | **P1** | **Thread counts pinned** | `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=1` set at import; documented |
| **NFR-11** | **P1** | **Stable sort with explicit tie-break** | All ranking paths use stable sort keyed on (score, parent_asin); no `set` iteration in ranking code |
| **NFR-14** | **P1** | **Dependency pinning with CPU-only wheels** | Exact versions pinned; CPU-only torch index or torch-free |
| NFR-7 | P2 | Memory footprint fits commodity CPU limits | Peak RSS recorded |

---

## 9. Milestones — anchored

Build window **29 Aug 12:00 → 1 Sep 12:00**. `H+n` = hours from window open. Verify the window against the official Info Document before relying on this.

> **Pre-window (26–29 Aug):** confirm what preparation is permitted under the rules before doing any. If pre-building is prohibited, M0's evaluator reading must happen inside the window — budget for it rather than assuming it away.

| Phase | Window | Deliverable | Exit criteria |
|---|---|---|---|
| **M0 — Characterise** | H+00 → H+04 | Kit cloned, SHA256 verified, baseline reproduced. **Read the evaluator end to end.** Enumerate the ten `ask_attribute` values. Inspect `user_profile` schema. Measure per-field missingness on the 50k slice. Determine whether MRR uses first-hit or best rank. | TechnicalScore 0.10671 reproduced; §12 internal questions all answered from source |
| **M1 — Floor** | H+04 → H+14 | Attribute-phrase index + constraint extraction + slot state + defensive parsing (FR-21) | ≥ 0.89 clean; **a submittable bundle exists on disk** |
| **M2 — Robustness** | H+14 → H+26 | bm25s route + dense route + weighted RRF fusion | **Ablation floor ≥ 0.70 (G-2)** |
| **M2.5 — Silent-failure gate** | H+26 → H+32 | Fusion truncation sized (FR-18); empty-pool recovery (FR-23); cross-session isolation test; repeat-ask test (FR-19); determinism check (NFR-9) | **All five pass before M3 opens.** Hard gate. |
| **M3 — Precision** | H+32 → H+44 | Reranker cascade with margin gate | Rank-1 share ≥ 79%; TechnicalScore ≥ 0.933; NFR-8 latency check passes |
| **M4 — Defensibility** | H+44 → H+54 | Information-gain question policy with stopping rule, dual-track routing, profile use, per-scenario ablations | Ablation table complete — including negative results |
| **M5 — Package** | H+54 → H+64 | README, technical report, demo video, Devpost writeup, disclosure statement | All §10 items complete |
| **FREEZE** | **H+64** | **Code freeze.** No functional changes after this point. | — |
| **M6 — Verify** | H+64 → H+72 | Clean-checkout reproduction with network disabled; two-run determinism check; final submission | NFR-1, NFR-2, NFR-9, NFR-13 all verified on a clean machine |

**Sequencing rationale.** M1 banks a submittable artefact within 14 hours — everything after that is upside on a score you already hold. M2 before M3 because robustness protects the score that counts, while precision only improves a score you may not keep. M2.5 is a hard gate because §6.5's failures are *silent*: they pass a smoke test and surface only at full-harness scale. M5 gets 10 hours because it carries more of the grade than M3 does (§2.1). M6 exists because "it worked on my machine" is how reproducible submissions die.

**If you fall behind:** cut M4 before M3, and cut M3 before M5. Never cut M6.

---

## 10. Deliverables

| # | Item | Requirements |
|---|---|---|
| 1 | Devpost written description | Problem approach, development tools, APIs used, libraries and frameworks, datasets and assets |
| 2 | Public GitHub repository | Commented code covering all components; README with overview, setup, reproduction steps, limitations reflection, team contributions |
| 3 | Demo video | End-to-end operation, public on YouTube, linked from Devpost, no third-party trademarks or copyrighted content. Backend walkthrough explicitly accepted in place of a UI |
| 4 | Technical report | Architecture, model choice, cost, latency, token usage, limitations |
| 5 | Disclosure statement | Network dependency (or independence), offline fallback behaviour, estimated cost |

### 10.1 Writeup guidance

**On §6 — be candid.** Frame it as: *we characterised the evaluation environment, measured our exposure to it, and hardened against the version we expect at judging.* That is true and it is the strongest available answer to Innovation & Problem Insight. Report the **ablation floor** as the headline robustness number (§6.6.1) — it is unfakeable and it pre-empts the question a judge would otherwise ask cold.

**On §6.4 — use +0.039, not +0.091.** With e-commerce search engineers on the panel, an inflated uplift claim is a liability.

**On §6.5 — put the edge cases in the limitations section even for the ones you fully closed.** Finding and closing them is itself the evidence of engineering judgement.

**On Impact & Relevance (20%, previously uncovered)** — the report needs a section that answers, without hedging:
- **Who.** A named shopper with a real problem ("knows roughly what they want, cannot phrase it as a search query, abandons after two failed searches").
- **Why this shape.** Ten turns is not a hackathon artefact — it is roughly the patience budget of a real shopper. Every turn spent asking is a turn not spent recommending. That tension is the actual product problem.
- **What generalises.** Zero marginal inference cost, no API dependency, sub-second CPU latency, no GPU — this runs on a phone or a commodity box, which matters for markets where a hosted-LLM copilot is not economic.
- **What doesn't.** Frozen catalog, English only, no cold-start items, no images. State it plainly.

---

## 11. Risks

| ID | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | Private simulator paraphrases utterances; template matching collapses | Med | Critical | M2 dense route; gate on **G-2 ablation floor** before M3 opens |
| R2 | Network disabled at final scoring breaks an LLM-dependent path | Med | Critical | NFR-1; entire scoring path offline; NFR-12 verified with network down |
| R3 | Judges read the code and see simulator fitting | Med | High | Genuine multi-route architecture; no evaluator imports in agent code; candid §6 writeup |
| R4 | Over-tuning to 200 public sessions doesn't generalise to 800 private | High | Med | Hold out a split; track per-scenario metrics, not the aggregate |
| R5 | Time sunk into MRR before robustness is secured | Med | High | M2.5 hard gate |
| R6 | Timeout or memory limits in the organiser's environment | Low | High | **FR-20 deadline guard** (survives it), NFR-4/NFR-7 (measures it) |
| R7 | Catalog or evaluator revised before the deadline | Low | Med | Pin the SHA256; re-verify at M6 |
| R8 | Reranker silently exceeds per-turn budget, scoring as timeout-miss | Med | High | NFR-8 isolated benchmark before adoption; FR-20 guard as backstop; margin-gated cascade |
| R9 | Module-level cache leaks state across sessions, corrupting results invisibly | Low | High | Explicit cross-session isolation test at M2.5 |
| **R10** | **`price="None"` or JSON-string `details` crashes the agent mid-harness** | **High** | **Critical** | **FR-21 defensive parsing, unit-tested against the literal sentinel** |
| **R11** | **Nondeterminism (BLAS threads / unstable argsort) makes the reported score irreproducible** | **Med** | **High** | **NFR-9–NFR-11; two-run byte-identity check at M2.5 and M6** |
| **R12** | **Embedding matrix or model weights exceed GitHub's 100 MiB blob limit at submission time** | **Med** | **High** | **NFR-13; decide the artefact strategy at M0, not M5. TDD §4.** |
| **R13** | **Offline model load hangs rather than errors under a firewall** | **Med** | **Critical** | **NFR-12; load from local path; verify with network physically disabled at M6** |
| **R14** | **Packaging compressed into the final hours; Impact/Presentation (30%) under-served** | **High** | **High** | **10h M5 block; H+64 freeze; cut M4 before M5** |

---

## 12. Open questions

### 12.1 Answerable by reading the shipped evaluator — do this at M0, not at the webinar

| ID | Question | Why it matters |
|---|---|---|
| A1 | What are the ten permitted `ask_attribute` values? | FR-12's information-gain policy cannot be designed without them |
| A2 | What fields does `user_profile` contain, and do they correlate with target attributes? | Validates or kills FR-14 in 20 minutes |
| A3 | Does MRR use the rank at first hit, or the best rank across the session? | Decides whether turn 1 should be an aggressive broad dump or conservative |
| A4 | What fraction of *your* 50k slice has empty `features` / `description` / `price`? | Sizes FR-22's fallback path; the dataset-wide 26.5% figure is not your slice |
| A5 | Are sessions run sequentially in one process? | Sizes the R9 state-leak risk |

### 12.2 Genuinely external — raise at the technical workshop, 28 Aug 16:00–16:45

| ID | Question | What it changes |
|---|---|---|
| Q1 | Do the private 800 sessions use the same utterance templates, or is paraphrasing applied? | The single highest-leverage answer available |
| Q2 | Will network access be disabled during final scoring? | Confirms or relaxes NFR-1 |
| Q3 | Are CPU, memory and per-turn timeout limits published? | Sets NFR-4, NFR-7, NFR-8 targets |
| Q4 | Is deriving attribute phrases from catalog metadata in scope? | Confirms the M1 approach |
| Q5 | Is TechnicalScore used directly in Technical Execution, or as one input? | Sets how hard to push past 0.933 |
| Q6 | Are real catalog brand names in the demo video acceptable under the no-trademarks clause? | Confirms deliverable 3 is safe as planned |
| **Q7** | **Are precomputed build artefacts (e.g. a committed embedding matrix) acceptable, or must the index build from raw catalog at runtime?** | **Decides the entire artefact strategy — see TDD §4 and R12** |
| **Q8** | **What preparation is permitted before the 29 Aug window opens?** | Determines whether M0 fits inside the 72h |

**If Q1 goes unanswered:** default to assuming paraphrasing is applied and do not scale back M2. The cost of being wrong conservatively (extra robustness work) is far below the cost of being wrong optimistically (a collapsed private score).

**If Q7 goes unanswered:** build the runtime path anyway (TDD §4 fallback). A system that builds from raw catalog in 60 s is acceptable under either answer; one that requires a committed 74 MB artefact is acceptable under only one.

---

## Appendix A — Measured baselines

Public set, 200 sessions. Full evaluation runtime 40 s.

| Configuration | Hit@10 | MRR | MTTC | Efficiency | TechnicalScore |
|---|---|---|---|---|---|
| BM25 starter (shipped) | 0.125 | 0.0680 | 9.81 | 0.119 | 0.10671 |
| Lexical attribute matcher | 0.995 | 0.6953 | 1.595 | 0.9405 | 0.89418 |
| Lexical matcher, paraphrased input | 0.220 | 0.157 | 8.99 | 0.201 | 0.1972 |
| **Full system, exact-phrase route ablated** | — | — | — | — | **TBD — G-2 gate** |

Lexical matcher, per scenario:

| Scenario | n | Hit@10 | MRR | MTTC |
|---|---|---|---|---|
| Buying | 80 | 0.988 | 0.670 | 1.21 |
| Browsing | 80 | 1.000 | 0.632 | 1.24 |
| Intent Override | 30 | 1.000 | 0.961 | 3.60 |
| Boundary | 10 | 1.000 | 0.602 | 1.50 |

Rank distribution (200 sessions): rank 1 = 112 · rank 2 = 27 · rank 3 = 19 · ranks 4–10 = 41 · miss = 1.

## Appendix B — Session composition

Identical mix across public and private splits: Buying 40% · Browsing 40% · Intent Override 15% · Boundary 5%.

Catalog: 50,000 products, `Clothing_Shoes_and_Jewelry`, Amazon Reviews 2023 (McAuley Lab, UCSD). Participant-visible fields: `parent_asin`, `title`, `features`, `description`, `price`, `categories`, `details`, `average_rating`, `rating_number`, `store`. Only `parent_asin` is scored.

## Appendix C — Evidence provenance

| Claim | Confidence | Basis |
|---|---|---|
| §6.1–§6.5 simulator behaviour and baselines | **High** | Directly measured against the shipped kit |
| §6.4 corrected uplift arithmetic | **High** | Derived from Appendix A rank distribution |
| §6.6.2 brute force ≥ ANN at 50k | **High** | Consistent across sources; also verifiable in 10 minutes |
| §6.6.3 bm25s vs rank_bm25 | **High** | Published benchmarks, large effect size |
| §6.6.8 `price="None"`, open-schema `details` | **High** | Official dataset card |
| §6.6.9 determinism sources | **High** | Well-documented behaviour |
| §6.6.7 CPU cross-encoder latency | **Low** | Sources conflict by ~40×; hardware-dependent. **Must be measured on the grader CPU** |
| §6.6.5 hybrid robustness deltas | **Medium** | Consistent direction, but from adjacent domains (patents, biomedical, open-domain QA) rather than e-commerce |
| Build window, prize structure, judging panel | **Medium** | Public sources; **verify against the official Info Document** |
| Track 4 rules text, allowed libraries | **Unverified** | Could not be independently located. Treat the Info Document as sole authority |
