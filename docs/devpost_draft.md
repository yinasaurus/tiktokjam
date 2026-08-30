# Devpost Draft: Shopping Copilot

## Project Description

This project is an offline conversational shopping agent for TikTok TechJam 2026
Track 4: Shopping Copilot. The agent receives a short user message and an
anonymized aggregate preference profile, then returns a ranked list of catalog
`parent_asin` values and, when useful, one structured clarification request.

The system is optimized for the official backend evaluator, not for a consumer
checkout UI. Each session has a hard 10-turn limit. The objective is to recover
the hidden purchased product as early and as highly ranked as possible.

## How It Addresses the Problem

Traditional keyword search is brittle when a shopper starts vague, changes
their mind, or gives constraints incrementally. This solution uses an offline
evaluator-aligned retrieval pipeline, with a hybrid research path kept available
for measured experiments:

- Intent-sensitive handling for Buying, Browsing, Intent Override, and Boundary
  scenarios.
- Category routing, exact phrase matching, cross-turn lexical overlap, and
  popularity backfill in the submitted default agent.
- Optional multi-route research path across BM25 lexical search, dense
  retrieval, fusion, and reranking.
- Dialog state tracking for accumulated slots, declined attributes, superseded
  preferences, and the latest user utterance.
- Reciprocal-rank fusion and reranking to convert broad candidate coverage into
  precise top-ranked recommendations.
- A deadline guard and degraded fallback so the agent returns valid catalog IDs
  instead of timing out.

## Technical Architecture

The official evaluator imports `from starter.agent import Agent`. The adapter in
`starter/agent.py` exports the offline fast submission agent by default and
keeps the heavier hybrid agent available as `HybridAgent` for experiments.

Main components:

- `agent/fast_agent.py`: submitted default path; offline category routing,
  exact intent-card signal, repeated clarification, override handling, and
  valid Top 10 fallback.
- `agent/catalog.py`: defensive parsing, normalization, product indexing, and
  popularity backfill for the hybrid research path.
- `agent/extract.py`: constraint extraction from the current utterance and
  session context.
- `agent/state.py`: per-session memory and slot lifecycle.
- `agent/routes/`: exact phrase, lexical BM25, and dense retrieval routes.
- `agent/fusion.py`: weighted reciprocal-rank fusion and popularity recovery.
- `agent/rerank.py`: heuristic reranking plus optional LightGBM model loading.
- `evaluator/local_evaluator.py`: official-style scoring for public sessions.

## Models and APIs Used

Default path:

- No hosted LLM API.
- No API key.
- No paid API calls.
- Zero token usage during scoring.
- CPU-only local Python stack.

Planned production model artifacts:

- Default submission path: no model artifact required; deterministic offline
  catalog indexing, clarification, and exact intent-card signal.
- Optional dense encoder: a vendored Model2Vec static encoder under
  `models/encoder/`, only if measured ablations improve the default.
- Optional reranker: LightGBM LambdaRank saved as `models/ltr.txt`, only if it
  beats the default on score and latency.

External hosted services are not part of the submission path. If the team later
tests an external model for learning only, credentials must be supplied locally
via environment variables and never committed, and the offline local path remains
the default submitted method.

## Libraries and Frameworks

- Python 3.11+
- `numpy`
- `scipy`
- `bm25s`
- `model2vec`
- `lightgbm`
- `pytest`
- Standard-library HTTP server for the optional local demo UI

## Dataset and Assets

The competition uses a frozen 50,000-product slice from the Amazon Reviews 2023
`Clothing_Shoes_and_Jewelry` category. The participant kit also includes 200
labeled public development sessions and a deterministic local evaluator. The
organizer keeps 800 additional private sessions for final scoring.

The project does not download or reconstruct the full upstream Amazon Reviews
2023 dataset. It uses the official participant kit release assets only:

- `catalog.jsonl.gz`
- `techjam-participant-kit.zip`
- `SHA256SUMS`

Local data files are gitignored and should not be committed.

## Evaluation Framing

- Coverage / HitRate@K: shows whether retrieval keeps the hidden purchased item
  inside the returned candidate set.
- Precision / MRR / top-rank share: shows whether reranking moves the exact
  purchased item toward rank 1.
- Efficiency / MTTC: shows whether the dialog policy converges in fewer turns
  and avoids unnecessary cognitive load.
- Cost / latency: shows commercial practicality. The default path is offline
  and reports zero token usage.

Internal submission gate: the team should only treat a method as submission-ready
when the official local evaluator or acceptance wrapper reports
`recommended_technical_score >= 0.80` without paid API calls, with valid Top 10
recommendations and acceptable latency.

Current measured public-set result for the default offline path:

- HitRate@10: 0.960000
- MRR: 0.681347
- MTTC: 2.585000
- TechnicalScore: 0.852704
- Token usage: 0

## How To Reproduce

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

.\scripts\setup_local_data.ps1 -DownloadOfficial
.\scripts\verify_submission.ps1 -WithData
.\scripts\package_submission.ps1
```

Optional model training:

```powershell
python scripts/train_ltr.py
python scripts/bench_reranker.py --mode ltr
```

## Limitations

- The catalog is frozen; the system does not handle cold-start products.
- Text only; no image or multimodal retrieval.
- English-only assumptions.
- The demo UI is not scored and is intended only for walkthroughs.
- Hybrid research ranker falls back to a heuristic unless `models/ltr.txt` has
  been trained and benchmarked.
- The current submission candidate avoids paid APIs and hosted model
  dependencies entirely.

## Future Improvements

- Complete Model2Vec vendoring and network-disabled verification.
- Train and benchmark the LightGBM LambdaRank reranker.
- Add a measured ablation appendix only if a new method beats the current
  offline default.
- Improve demo explanations for matched constraints and intent routing without
  changing the scored backend API.
- Calibrate question policy thresholds against per-scenario evaluator results.

## Team Contributions

Fill before submission:

- Team member 1:
- Team member 2:
- Team member 3:
- Team member 4:
