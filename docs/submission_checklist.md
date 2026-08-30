# Submission Checklist

## Public Repository

- [ ] `README.md` includes overview, setup, reproduction, limitations, and team
  contributions.
- [ ] `starter/agent.py` exports the final `Agent`.
- [ ] `evaluator/` is unchanged from the participant kit unless explicitly
  allowed.
- [ ] `data/catalog.jsonl`, `data/public_set.jsonl`, `results.json`,
  `eval_output/`, caches, `.env`, and credentials are not committed.
- [ ] No paid API call is required for setup, evaluation, demo, or submission.
- [ ] Best submitted method is chosen from measured ablations, not intuition.
- [ ] GitHub Actions fixture CI is green.
- [ ] Local official-data acceptance check reaches
  `recommended_technical_score >= 0.80`.
- [ ] `models/encoder/` contains only acceptable model artifacts under platform
  limits, or the README clearly describes local setup.
- [ ] `models/ltr.txt` is committed only after measured score and latency
  improvement.

## Local Verification

Run before submission:

```powershell
python -m pytest tests -q
python -m compileall agent scripts evaluator ui -q
.\scripts\setup_local_data.ps1
.\scripts\evaluate.ps1
python scripts/synthetic_customer_gate.py --threshold 0.80 --trials 100
python scripts/run_ablations.py
python scripts/bench_reranker.py --mode heuristic
python scripts/check_acceptance.py --threshold 0.80
python scripts/check_determinism.py
git status --short
```

If `models/ltr.txt` exists:

```powershell
python scripts/bench_reranker.py --mode ltr
python scripts/run_ablations.py --variant ltr --variant cascade
```

## Devpost

- [ ] Problem statement and solution approach are clear.
- [ ] Tools, APIs, libraries, datasets, and assets are listed.
- [ ] State that no hosted model/API is required for the default scoring path.
- [ ] Mention Amazon Reviews 2023 and the frozen participant-kit catalog slice.
- [ ] Include measured HitRate@10, MRR, MTTC, Efficiency, TechnicalScore,
  latency, and token usage.
- [ ] Include limitations and future improvements.
- [ ] Include team member contributions.

## Demo Video

- [ ] Uploaded to YouTube with public visibility.
- [ ] Linked from Devpost.
- [ ] Shows end-to-end evaluator or API usage.
- [ ] Shows at least one multi-turn interaction.
- [ ] Explains Coverage, Precision, and Efficiency metrics.
- [ ] Mentions the local/offline default path and no paid API requirement.
- [ ] Avoids unnecessary third-party trademarks or copyrighted material.
