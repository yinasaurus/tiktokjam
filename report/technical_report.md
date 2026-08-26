# Technical report (draft)

TikTok TechJam 2026, Track 4. Fill during M5. Do not invent numbers — paste from `scripts/run_ablations.py` and the isolated reranker bench.

## Who this is for

A shopper who knows roughly what they want, cannot phrase it as a keyword query, and abandons after two failed searches. Ten turns is not a hackathon artefact; it is roughly the patience budget of that person. Every turn spent asking is a turn not spent recommending.

## Architecture

See TDD §1. Six components plus a deadline guard. Three independent retrieval routes (exact-phrase, bm25s, dense brute-force numpy). No ANN. No evaluator imports.

## Model choice

Default encoder: Model2Vec static (`potion-retrieval-32M` class) — torch-free, sub-second 50k encode, weights well under 100 MiB. Escalate to ONNX-int8 MiniLM only if dense-route Recall@50 trails MiniLM by more than 3 points on the holdout (TDD D1).

Reranker: LightGBM LambdaRank as the default path. Cross-encoder is gated and must earn its place on an isolated p95 < 150 ms bench (TDD D2). Until that model is trained, a linear heuristic over the same features ships so the cascade structure is real.

## Cost, latency, tokens

| Item | Value | Source |
|---|---|---|
| Tokens / session | 0 | offline path |
| Per-turn p95 | _measure_ | NFR-4 |
| 200-session wall | _measure_ | NFR-6 |
| Peak RSS | _measure_ | NFR-7 |
| Index cold-start | _measure_ | NFR-4 |

## Ablation floor (G-2)

TechnicalScore with `exact_phrase_enabled=False`: **TBD**. This is the headline robustness number, not a self-authored paraphrase gap.

Rerank uplift must be reported as **+0.039** to the 79% rank-1 target, not the +0.091 perfect-reranking ceiling (PRD §6.4).

## What generalises

Zero marginal cost, no API dependency, sub-second CPU, no GPU. The same pipeline runs on a phone or a commodity box.

## What does not

Frozen catalog. English only. No cold-start items. No images. `retain_superseded=True` is simulator-specific and called out as such.

## Limitations (including the ones we closed)

See PRD §6.5 and TDD §17. Put every silent failure mode here even if the test is green: fusion truncation, empty pool, cross-session leak, unstable argsort, `price="None"`, phrase-normaliser mismatch, offline model-load hang.
