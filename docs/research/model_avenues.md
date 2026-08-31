# Research Avenues: Dense Retrieval and LightGBM Reranking

Team: **kpopy demon hunter**

Branch: `research/dense-ltr-marketplaces`

Reason for this branch: keep `main` stable while we investigate the two Slide 4
research methods that are not the submitted default.

Bottom line today: submit the offline `FastAgent` rank tie-break PR unless
dense retrieval or LightGBM reranking beats `0.908232` on the full
official-style evaluator with zero paid API calls.

## 1. Current Truth

| Item | Value |
|---|---:|
| Current official clean TechnicalScore | 0.908232 |
| Current clean HitRate@10 | 1.000000 |
| Current clean MRR | 0.729107 |
| Current clean MTTC | 1.525000 |
| Current paraphrased robustness TechnicalScore | 0.844094 |
| Current paraphrased HitRate@10 | 0.955000 |
| Paid API calls | 0 |
| Current submitted default | `starter.agent.Agent` -> `agent.fast_agent.Agent` |

Important: the latest rank tie-break research now shows 90%+ official
TechnicalScore on the public evaluator. It is still not 95%; the remaining
gap is mostly MRR.

## 2. What We Are Using Today

| Layer | Current default | What that means |
|---|---|---|
| Model | No hosted LLM and no paid API | Deterministic offline code, zero token usage. |
| Search | Category + exact constraint + lexical/token scoring | More like a ranked retrieval system than a chatbot. |
| Ranking | Weighted score with deterministic fallback | Sort products and always return 10 valid IDs. |
| BM25 | Present in research/hybrid path | Not the default fast submission path. |
| Dense embeddings | Present as optional `agent/routes/dense.py` | Needs a local encoder artifact to be meaningful on 50k catalog. |
| LightGBM | Present as optional training/rerank scripts | Needs measured improvement before submission. |

## 3. TechnicalScore 95% Reality Check

To reach `TechnicalScore = 0.95`, we likely need all three:

| Metric | Current | Rough target for 0.95 |
|---|---:|---:|
| HitRate@10 | 1.000 | about 1.000 |
| MRR | 0.729 | about 0.900 |
| MTTC | 1.525 | about 2.000 or lower |

This is a large jump. The biggest remaining gap is ranking precision: the target
product must appear closer to rank 1, not just somewhere in Top 10.

## 4. Avenue A: Dense / Model2Vec Retrieval

| Question | Answer |
|---|---|
| Goal | Improve recall and semantic matching when exact words differ. |
| Candidate model | Local Model2Vec encoder under `models/encoder/`. |
| Paid API? | No. Must be downloaded locally and committed only if size/licence are acceptable. |
| Current implementation | `agent/routes/dense.py` supports `Model2VecEncoder`; tiny fixtures use `HashEncoder`. |
| Risk | Embedding 50k products at startup may be slow unless cached/precomputed. |
| Submission rule | Only use if full public-set TechnicalScore beats `0.908232`. |

Commands:

```powershell
python scripts\build_index.py
python scripts\run_ablations.py --variant full --variant no_dense
```

macOS/Linux:

```bash
python scripts/build_index.py
python scripts/run_ablations.py --variant full --variant no_dense
```

Decision rule:

| Result | Decision |
|---|---|
| Dense improves MRR without hurting HitRate/MTTC | Consider enabling. |
| Dense is slower and score is flat/lower | Keep research-only. |
| Dense requires network at scoring time | Reject. |

## 5. Avenue B: LightGBM LambdaRank Reranker

| Question | Answer |
|---|---|
| Goal | Move the correct product closer to rank 1. |
| Model | Local LightGBM LambdaRank model saved as `models/ltr.txt`. |
| Paid API? | No. Training is local. |
| Current implementation | `scripts/train_ltr.py`, `agent/rerank.py`, `agent/rank_features.py`. |
| Risk | Only 200 public sessions; high overfit risk. |
| Submission rule | Only use if full public-set TechnicalScore beats `0.908232` and latency is acceptable. |

Commands:

```powershell
python scripts\train_ltr.py --output eval_output\ltr_research\ltr.txt --metadata eval_output\ltr_research\metadata.json
python scripts\bench_reranker.py --mode ltr --ltr-model eval_output\ltr_research\ltr.txt
python scripts\run_ablations.py --variant ltr --variant cascade --ltr-model eval_output\ltr_research\ltr.txt
```

macOS/Linux:

```bash
python scripts/train_ltr.py --output eval_output/ltr_research/ltr.txt --metadata eval_output/ltr_research/metadata.json
python scripts/bench_reranker.py --mode ltr --ltr-model eval_output/ltr_research/ltr.txt
python scripts/run_ablations.py --variant ltr --variant cascade --ltr-model eval_output/ltr_research/ltr.txt
```

Decision rule:

| Result | Decision |
|---|---|
| LTR improves MRR and TechnicalScore on full public set | Consider submission, but disclose overfit risk. |
| LTR improves public score only by memorizing public sessions | Reject for final story/private transfer. |
| LTR hurts HitRate or MTTC | Reject. |

## 6. Branch Acceptance Gate

Before merging any research back to `main`:

```powershell
python -m pytest tests -q
python -m compileall agent scripts tools starter tests evaluator ui -q
python scripts\check_repo_hygiene.py
python tools\eval.py
```

Accept only if:

| Gate | Required |
|---|---|
| Official clean TechnicalScore | Greater than `0.908232` |
| Internal minimum | At least `0.80` |
| Paid API calls | 0 |
| Token usage | 0 |
| Data hygiene | No local catalog/session/result/cache committed |
| Demo UI | Still works in fixture mode |

## 7. Research Summary So Far

| Track | Status | Current decision |
|---|---|---|
| Dense / Model2Vec | Implementation hooks exist; meaningful benchmark needs local encoder artifact. | Keep research-only until benchmarked. |
| LightGBM LTR | Training and benchmark scripts exist; needs full public-set proof. | Keep research-only until it beats default. |
| Marketplace research | Taobao/Lazada/Shopee/Amazon support our hybrid conversational retrieval story. | Add to docs/story, not a score change by itself. |

## 8. Quick Branch Ablation Evidence

Command run on this branch:

```powershell
python scripts\run_ablations.py --variant full --variant no_dense --variant lexical_only --limit 30
```

Result:

| Variant | HitRate@10 | MRR | MTTC | TechnicalScore | Read |
|---|---:|---:|---:|---:|---|
| `full` hybrid path | 0.800000 | 0.689815 | 3.933333 | 0.748278 | Below default. |
| `no_dense` | 0.766667 | 0.681481 | 4.466667 | 0.718444 | Dense helped this small slice, but not enough. |
| `lexical_only` | 0.100000 | 0.041429 | 10.000000 | 0.082429 | Not viable. |
| fast default before tie-breaks | 0.960000 | 0.681347 | 2.585000 | 0.852704 | Previous default. |
| fast rank tie-break PR candidate | 1.000000 | 0.729107 | 1.525000 | 0.908232 | Current best measured path. |

Interpretation:

| Finding | Consequence |
|---|---|
| Hybrid `full` underperforms fast default on the quick 30-session run. | Do not switch default agent. |
| Dense appears useful inside hybrid because `full` beats `no_dense` on this slice. | Continue dense research only if local encoder/cache can keep latency sane. |
| Lexical-only hybrid path collapses. | Ranking needs exact/state/fallback signals. |
| Current fast rank tie-break path is now the strongest measured submission path. | Open a PR for review; do not merge without teammate approval. |

An earlier local heuristic reranker benchmark artifact also showed
`TechnicalScore 0.555500` on a 20-session slice with p95 latency above 2s, so
reranking research must prove both score and latency before merge.

LightGBM probe on this machine:

```powershell
python scripts\bench_reranker.py --mode heuristic --limit 20 --output eval_output\ltr_research_heuristic_n20.json
python scripts\bench_reranker.py --mode ltr --limit 20 --output eval_output\ltr_research_ltr_nomodel_n20.json
```

Result: the 20-session research heuristic scored `0.555500`, and `ltr` mode
without a trained model scored `0.544167`. After installing `lightgbm==4.6.0`,
the import still stalled in this global Python environment, and a tiny
`train_ltr.py --limit 5` run produced no output before being stopped. See
`docs/research/lambdarank_probe.md` for the exact commands and next steps.

This means LTR research should resume from a fresh virtual environment with
`python -m pip install -r requirements.txt`. This does not affect the submitted
default fast agent.

Branch script support:

| Script | Research-only addition |
|---|---|
| `scripts/bench_reranker.py` | Adds `--ltr-model` so a local model artifact can live under ignored `eval_output/`. |
| `scripts/run_ablations.py` | Adds `--ltr-model` for `ltr` and `cascade` variants without changing default paths. |
