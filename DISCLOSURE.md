# Disclosure statement

TikTok TechJam 2026, Track 4 — Conversational Shopping Agent.

## Network dependency

**None at scoring time.** Retrieval, fusion, reranking, and question selection are local. There are no API keys and no hosted-model calls on the `respond()` path.

Environment pins (set at import, before numpy):

- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`
- `HF_DATASETS_OFFLINE=1`
- `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`

Models, when present, load from an explicit local directory (`models/encoder/`), never from a Hugging Face repo id.

## Offline fallback

If a stage fails or the per-turn budget is exhausted, the agent degrades rather than raising:

1. skip semantic fallback / dense / rerank / question, in that order
2. fuse whatever routes already returned
3. backfill from a static popularity list (`rating_count`, `avg_rating`, `parent_asin`)

Every rung returns `min(top_k, |catalog|)` unique catalog-resident ASINs and non-negative `usage` counts.

## Estimated cost

Zero marginal inference cost per session. No tokens are billed. `usage` is reported as zeros so the harness contract is satisfied (FR-4, FR-24).
