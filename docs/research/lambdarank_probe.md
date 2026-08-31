# LightGBM LambdaRank Probe

Team: **kpopy demon hunter**

Scope: investigate whether the existing LightGBM/LambdaRank research path can
realistically beat the current default `TechnicalScore 0.955300` without paid
API calls.

## 1. Short Answer

Do **not** switch the submission to LightGBM yet.

| Check | Result | Decision |
|---|---:|---|
| Current default score to beat | 0.955300 | Confidence-gated FastAgent remains stronger. |
| Research heuristic reranker, 20-session slice | 0.555500 | Too low. |
| LTR mode without trained model, 20-session slice | 0.544167 | Too low. |
| LightGBM dependency | Installed locally, then import stalled | Environment risk. |
| Full public-set research ablation | Started, did not finish in practical time | Not ready. |
| Default submission path changed? | No | Keep `starter.agent.Agent` as-is. |

## 2. What This LTR Path Actually Uses

| Layer | Current implementation |
|---|---|
| Candidate generator | `agent.agent.Agent`, not the submitted `agent.fast_agent.Agent`. |
| Lexical route | `bm25s` BM25 over normalized catalog text. |
| Dense route | Optional Model2Vec encoder if `models/encoder/` exists; otherwise unavailable for the 50k catalog. |
| Fusion | Weighted reciprocal-rank fusion in `agent/fusion.py`. |
| Default reranker | Hand-written heuristic in `agent/rank_features.py`. |
| LTR reranker | LightGBM `Booster` loaded from `Config.ltr_model_path`. |
| Features | 13 numeric features: fused score, constraint coverage, category match, title overlap, rating/popularity, sparse listing flag, gender match/mismatch, unmatched-constraint flag, price-present flag. |

This is not training a chatbot or language model. It is a local learning-to-rank
model that reorders already-retrieved products.

## 3. Files Inspected

| File | Finding |
|---|---|
| `scripts/train_ltr.py` | Generates LambdaRank rows from public sessions and writes a local model artifact. |
| `scripts/bench_reranker.py` | Benchmarks `agent.agent.Agent` modes and latency. Patched to accept `--ltr-model`. |
| `scripts/run_ablations.py` | Runs research variants. Patched to accept `--ltr-model`. |
| `agent/rerank.py` | `ltr`/`cascade` load a LightGBM model if present, otherwise fall back to heuristic rerank. |
| `agent/rank_features.py` | Defines shared heuristic/LTR feature vector. |
| `requirements.txt` | Pins `lightgbm==4.6.0`; no paid API dependency. |
| `starter/agent.py` | Still points to `agent.fast_agent.Agent`; untouched. |

## 4. Commands Run

```powershell
git switch -c research/lightgbm-lambdarank
python scripts\run_ablations.py --variant full --variant no_rerank --variant ltr --variant cascade --output-dir eval_output\ltr_research --progress-every 1
python scripts\bench_reranker.py --mode heuristic --limit 20 --output eval_output\ltr_research_heuristic_n20.json
python scripts\bench_reranker.py --mode ltr --limit 20 --output eval_output\ltr_research_ltr_nomodel_n20.json
python -m pip install lightgbm==4.6.0
$env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; python -c "import lightgbm, numpy; print('lightgbm', lightgbm.__version__)"
python scripts\train_ltr.py --limit 5 --candidates-per-turn 20 --output eval_output\ltr_research\ltr_probe.txt --metadata eval_output\ltr_research\ltr_probe_metadata.json
python -m compileall scripts\bench_reranker.py scripts\run_ablations.py scripts\train_ltr.py agent\rerank.py agent\rank_features.py -q
python -m pytest tests\test_ranking.py tests\test_starter_entry.py tests\test_min_results.py -q
python scripts\check_repo_hygiene.py
```

Stopped commands:

| Command | Why stopped |
|---|---|
| Full `run_ablations.py` over 200 sessions | No first-variant result after several minutes. |
| LightGBM import probe | Import still silent after 30 seconds, even with thread caps. |
| Tiny `train_ltr.py --limit 5` | No output after 30 seconds, before dataset loading. |

## 5. Measured Research Results

| Run | Sessions | HitRate@10 | MRR | MTTC | TechnicalScore | Mean latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Research heuristic reranker | 20 | 0.600000 | 0.541667 | 6.350000 | 0.555500 | 858.760 ms | 2024.382 ms |
| `ltr` mode, no model artifact | 20 | 0.600000 | 0.463889 | 5.750000 | 0.544167 | 949.964 ms | 2501.003 ms |

The 20-session slice is not enough for final scoring, but it is enough to reject
LTR as a rushed submission candidate: it is slower and far below the current
default full public-set score.

## 6. What Blocks LTR Submission

| Blocker | Why it matters |
|---|---|
| No trained model benchmark beat `0.955300`. | The project rule says we only submit the best measured method. |
| Local LightGBM import stalls after installation. | Training and scoring are not reproducible on this machine yet. |
| Full research ablation did not finish quickly. | Deadline risk and demo risk. |
| Training data is only 200 public sessions. | High overfit risk; private transfer is uncertain. |
| LTR path benchmarks `agent.agent.Agent`, not `agent.fast_agent.Agent`. | A win there does not automatically mean the default submission improves. |
| Latency is already high before a trained model helps. | p95 above 2 seconds is risky for a headless evaluation deadline. |

## 7. Safe Next Command

Use a fresh virtual environment before continuing. The current global Python
environment has broken package warnings and LightGBM import stalls.

Windows:

```powershell
python -m venv .venv-ltr
.\.venv-ltr\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\train_ltr.py --candidates-per-turn 50 --output eval_output\ltr_research\ltr.txt --metadata eval_output\ltr_research\metadata.json
python scripts\run_ablations.py --variant full --variant ltr --variant cascade --ltr-model eval_output\ltr_research\ltr.txt --output-dir eval_output\ltr_research
```

macOS/Linux:

```bash
python3 -m venv .venv-ltr
. .venv-ltr/bin/activate
python -m pip install -r requirements.txt
python scripts/train_ltr.py --candidates-per-turn 50 --output eval_output/ltr_research/ltr.txt --metadata eval_output/ltr_research/metadata.json
python scripts/run_ablations.py --variant full --variant ltr --variant cascade --ltr-model eval_output/ltr_research/ltr.txt --output-dir eval_output/ltr_research
```

Merge rule: only consider enabling LTR if the full public-set run improves
TechnicalScore above `0.955300`, keeps HitRate@10 at least `1.000000`, and has
acceptable latency.

## 8. Sources

| Source | Why it matters |
|---|---|
| https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.LGBMRanker.html | Confirms `LGBMRanker` supports the `lambdarank` ranking objective and grouped query data. |
| https://lightgbm.readthedocs.io/en/latest/Parameters.html | Confirms learning-to-rank needs query/group information and that deterministic mode can slow training. |
