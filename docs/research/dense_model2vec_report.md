# Dense / Model2Vec Research Report

Team: **kpopy demon hunter**

Branch scope: dense/Model2Vec research only. This branch does not change
`starter/agent.py` or the default submission behavior.

## Executive Decision

Do **not** switch the submission to dense retrieval yet.

Dense/Model2Vec is a good offline research avenue, but this workspace is not
ready to prove it can beat the current clean TechnicalScore of `0.908232`.
The current 50k-catalog agent has no usable local Model2Vec encoder, so dense
embeddings are not active in the measured default.

## Current Facts

| Check | Result | Meaning |
|---|---:|---|
| Current clean TechnicalScore to beat | `0.908232` | Any dense change must beat this on the full official public set. |
| Current clean HitRate@10 | `1.000000` | The latest branch now reaches every public target in Top 10. |
| `requirements.txt` declares `model2vec==0.6.0` | Yes | Dependency is planned. |
| `models/encoder/` contains complete model files | No | Only README is present, so production dense cannot run. |
| `agent.routes.dense.Model2VecEncoder` exists | Yes | The code path can load a local `StaticModel`. |
| `agent.agent.Agent` uses dense on 50k without model files | No | `dense.available=False`, `encoder=None`. |
| Tiny fixture dense test path exists | Yes | Uses `HashEncoder`, not production Model2Vec. |

## What The Code Uses Today

| Layer | Current state |
|---|---|
| Default submission entry | `starter.agent.Agent` |
| Submitted fast path | `agent.fast_agent.Agent` |
| Paid APIs | None |
| Hosted LLM | None |
| BM25 / `bm25s` | Optional research path, not active in this shell |
| Dense / Model2Vec | Optional research path, not active without local encoder files |
| Ranker | Deterministic exact/state/token/popularity logic in the default fast path |

## Dense Code Path

| File | Role | Status |
|---|---|---|
| `agent/routes/dense.py` | Defines `Model2VecEncoder`, `HashEncoder`, and brute-force matrix scoring. | Wired, but needs model files. |
| `scripts/build_index.py` | Builds catalog cache and writes dense embedding `.npz` when an encoder loads. | Works as a readiness check; cache is not yet wired into default `Agent` startup. |
| `scripts/run_ablations.py` | Compares `full`, `no_dense`, `lexical_only`, etc. | Useful, but full runs are slow on this shell. |
| `models/encoder/README.md` | Says the encoder directory must hold a complete local model. | Correct constraint. |
| `requirements.txt` | Pins `model2vec==0.6.0`. | Install needed in the benchmark environment. |

## Measurements Run

### Readiness Probe

Command:

```powershell
python -u -c "import time; from pathlib import Path; from agent.agent import Agent; t=time.perf_counter(); a=Agent('data/catalog.jsonl'); print('init_s', round(time.perf_counter()-t,3)); print('catalog', len(a.catalog)); print('lexical', getattr(a.lexical,'available',None)); print('dense', getattr(a.dense,'available',None)); print('encoder', type(a.encoder).__name__ if a.encoder else None); print('encoder_dir_exists', Path('models/encoder').exists()); print('encoder_dir_items', len(list(Path('models/encoder').iterdir())) if Path('models/encoder').exists() else 0)"
```

Result:

| Field | Value |
|---|---:|
| Init time | `25.236s` |
| Catalog size | `50000` |
| Lexical available | `False` |
| Dense available | `False` |
| Encoder | `None` |
| Encoder dir exists | `True` |
| Encoder dir items | `1` |

### Import Probe

Command:

```powershell
python -u -c "import importlib.util as u; mods=['numpy','model2vec','bm25s','lightgbm']; [print(m, bool(u.find_spec(m))) for m in mods]"
```

Result:

| Package | Available |
|---|---:|
| `numpy` | True |
| `model2vec` | False |
| `bm25s` | False |
| `lightgbm` | True |

### Index Builder

Command:

```powershell
python scripts\build_index.py --catalog data\catalog.jsonl --cache-dir cache
```

Result:

| Field | Value |
|---|---:|
| Catalog products | `50000` |
| Phrase vocab | `324336` |
| Sparse listings | `9007` |
| Encoder loaded | No |
| Dense cache written | No |

Output ended with:

```text
no vendored encoder at models/encoder - skipping dense cache
```

### Tiny Ablation Smoke

Command:

```powershell
python scripts\run_ablations.py --variant full --variant no_dense --variant lexical_only --limit 5 --output-dir eval_output\dense_research
```

Result:

| Variant | HitRate@10 | MRR | MTTC | TechnicalScore | Read |
|---|---:|---:|---:|---:|---|
| `full` | `0.600000` | `0.500000` | `5.600000` | `0.558000` | Too small to trust. |
| `no_dense` | `1.000000` | `0.728571` | `2.800000` | `0.882571` | Better on first 5 only. |
| `lexical_only` | `0.000000` | `0.000000` | `11.000000` | `0.000000` | Not viable in this shell. |

This is not enough evidence to choose dense. It also shows `full` and
`no_dense` can diverge even when no dense encoder is active, likely because of
latency/budget or route-side interactions. Full public-set benchmarking is
required before any merge.

## External Model Research

Primary sources checked:

| Source | Useful fact |
|---|---|
| https://github.com/MinishLab/model2vec | Model2Vec creates small static embedding models from sentence transformers and is built for fast local embeddings. |
| https://huggingface.co/minishlab/potion-retrieval-32M | Retrieval-tuned Model2Vec model; local loading uses `StaticModel.from_pretrained`. Hugging Face lists about `131 MB`. |
| https://huggingface.co/minishlab/potion-base-8M | Smaller local Model2Vec model. Hugging Face lists about `61.4 MB`, better fit for the repo's under-100 MiB note. |

## What Blocks Dense Submission

| Blocker | Why it matters | Fix |
|---|---|---|
| No local encoder files | Production dense cannot run. | Download a complete Model2Vec model into `models/encoder/`. |
| `model2vec` missing in current shell | `Model2VecEncoder` cannot import. | Use a clean venv and `python -m pip install -r requirements.txt`. |
| Dense embedding cache not loaded by `Agent` | `build_index.py` writes `.npz`, but `agent.agent.Agent` does not read it. | Either wire cache loading in research branch or accept startup embedding cost. |
| `potion-retrieval-32M` is about 131 MB | Exceeds the repo note asking encoder files to stay under 100 MiB. | Test `potion-base-8M` first or document external download. |
| Full ablation slow on this shell | We need a full 200-session result, not a 5-session smoke. | Run in a clean environment with dependencies installed. |

## Exact Next Command To Benchmark

First prepare a clean environment and local model:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "from model2vec import StaticModel; m=StaticModel.from_pretrained('minishlab/potion-base-8M'); m.save_pretrained('models/encoder')"
```

Then run the dense benchmark:

```powershell
python scripts\dense_readiness.py --init-agent
python scripts\build_index.py --catalog data\catalog.jsonl --cache-dir cache
python scripts\run_ablations.py --variant full --variant no_dense --variant lexical_only --output-dir eval_output\dense_model2vec_full
```

macOS/Linux:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -c "from model2vec import StaticModel; m=StaticModel.from_pretrained('minishlab/potion-base-8M'); m.save_pretrained('models/encoder')"
python scripts/dense_readiness.py --init-agent
python scripts/build_index.py --catalog data/catalog.jsonl --cache-dir cache
python scripts/run_ablations.py --variant full --variant no_dense --variant lexical_only --output-dir eval_output/dense_model2vec_full
```

Acceptance rule:

| Result | Decision |
|---|---|
| Full public-set TechnicalScore beats `0.908232`, with HR@10 not lower and acceptable latency | Consider merging dense path. |
| Dense improves MRR but hurts HitRate or MTTC | Reject for submission. |
| Dense needs network during scoring | Reject for submission. |
| Dense cannot finish full public-set benchmark quickly | Keep research-only. |
