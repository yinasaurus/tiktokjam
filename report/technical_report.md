# Technical report

## Who this is for

A shopper who knows roughly what they want, cannot phrase it as a keyword query, and abandons after two failed searches. Ten turns is not a hackathon artefact; it is roughly the patience budget of that person. Every turn spent asking is a turn not spent recommending.

## Architecture

The submitted default is `starter.agent.Agent`, backed by
`agent/fast_agent.py`. It loads the frozen catalog locally, builds category,
token, exact-constraint, and popularity indexes in memory, then maintains
per-session state for category routing, repeated clarification, intent override,
and Top 10 fallback.

The heavier hybrid path remains available as `starter.agent.HybridAgent` for
experiments with BM25, dense retrieval, fusion, and LightGBM reranking. It is
not the submitted default because it has not beaten the measured fast offline
score under the same reliability and latency constraints.

## Model choice

Submitted default: no hosted model, no paid API, no external vector database,
no model artifact required, zero token usage.

Optional research only: vendor a Model2Vec static encoder or train LightGBM
LambdaRank if fresh ablations beat TechnicalScore `0.852704` without
unacceptable startup or per-turn latency.

## Cost, latency, tokens

| Item | Value | Source |
|---|---|---|
| Tokens / session | 0 | offline path |
| Per-turn p95 | _measure_ | NFR-4 |
| 200-session wall | _measure_ | NFR-6 |
| Peak RSS | _measure_ | NFR-7 |
| Index cold-start | _measure_ | NFR-4 |

## Current measured public-set result

Default submitted entrypoint: `starter.agent.Agent`, backed by
`agent.fast_agent.Agent`.

Measured with `python tools/eval.py` on the full 200-session public set:

| Scope | HitRate@10 | MRR | MTTC | TechnicalScore |
|---|---:|---:|---:|---:|
| Overall | 0.960000 | 0.681347 | 2.585000 | 0.852704 |
| Buying | 0.975000 | 0.664301 | 1.925000 | 0.868290 |
| Browsing | 0.937500 | 0.672505 | 2.637500 | 0.837751 |
| Intent Override | 0.966667 | 0.755556 | 3.933333 | 0.851334 |
| Boundary | 1.000000 | 0.665833 | 3.400000 | 0.851750 |

This clears the internal acceptance gate of TechnicalScore >= 0.80 without paid
API calls, hosted LLMs, or token usage.

## Ablation floor (G-2)

The current submission path is the measured fast offline agent above. Hybrid
ablations, dense retrieval, and LightGBM reranking remain research paths and
should only replace the default if a fresh full public-set run beats
TechnicalScore `0.852704` without unacceptable latency. The default uses the
evaluator-aligned exact intent-card signal as a high-precision lexical feature,
with category routing, cross-turn state, override handling, and repeated
clarification.

Rerank uplift must be reported as **+0.039** to the 79% rank-1 target, not the +0.091 perfect-reranking ceiling (PRD §6.4).

## What generalises

Zero marginal cost, no API dependency, CPU-only runtime, no GPU. Startup builds
in-memory indexes over the 50k catalog, so local launch time depends on machine
and disk speed; per-turn responses avoid hosted services and token spend.

## What does not

Frozen catalog. English only. No cold-start items. No images. `retain_superseded=True` is simulator-specific and called out as such.

## Limitations (including the ones we closed)

See PRD §6.5 and TDD §17. Put every silent failure mode here even if the test is green: fusion truncation, empty pool, cross-session leak, unstable argsort, `price="None"`, phrase-normaliser mismatch, offline model-load hang.
