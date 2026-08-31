# Submission Checklist

## Public Repository

- [ ] Any open final PR is reviewed by the team and merged to `main`.
- [ ] Final packaging is run from merged `main`, not only from the review
  branch.
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
  `recommended_technical_score >= 0.80`; current expected score is `0.955300`.
- [ ] `models/encoder/` contains only acceptable model artifacts under platform
  limits, or the README clearly describes local setup.
- [ ] `models/ltr.txt` is committed only after measured score and latency
  improvement.
- [ ] Submission archive, if used, is built from tracked files only with
  `scripts/package_submission.ps1` or `scripts/package_submission.sh`.
- [ ] Submission archive checksum `.zip.sha256` is generated and kept beside
  the final zip.
- [ ] `docs/final_submission_handoff.md` has the current commit and final
  command sequence.

## Local Verification

Run before submission:

```powershell
python -m pytest tests -q
python -m compileall agent scripts tools starter tests evaluator ui -q
.\scripts\setup_local_data.ps1
.\scripts\evaluate.ps1
python scripts/synthetic_customer_gate.py --threshold 0.80 --trials 100
python scripts/check_acceptance.py --threshold 0.80
python scripts/check_determinism.py
git status --short
```

Optional research checks:

```powershell
python scripts/run_ablations.py
python scripts/bench_reranker.py --mode heuristic
.\scripts\verify_submission.ps1 -WithData -WithResearch
```

If `models/ltr.txt` exists:

```powershell
python scripts/bench_reranker.py --mode ltr
python scripts/run_ablations.py --variant ltr --variant cascade
```

## Devpost

- [ ] Team name is set to `kpopy demon hunter`.
- [ ] Problem statement and solution approach are clear.
- [ ] Tools, APIs, libraries, datasets, and assets are listed.
- [ ] State that no hosted model/API is required for the default scoring path.
- [ ] Mention Amazon Reviews 2023 and the frozen participant-kit catalog slice.
- [ ] Include measured HitRate@10, MRR, MTTC, Efficiency, TechnicalScore,
  latency, and token usage.
- [ ] Include limitations and future improvements.
- [ ] Include individual team member contributions.

## Demo Video

- [ ] Uploaded to YouTube with public visibility.
- [ ] Linked from Devpost.
- [ ] Shows end-to-end evaluator or API usage.
- [ ] Shows at least one multi-turn interaction.
- [ ] Explains Coverage, Precision, and Efficiency metrics.
- [ ] Mentions the local/offline default path and no paid API requirement.
- [ ] Avoids unnecessary third-party trademarks or copyrighted material.
