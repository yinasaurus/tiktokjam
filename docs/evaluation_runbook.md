# Evaluation and Demo Runbook

This is the teammate-friendly runbook for final checks, demo recording, and
Devpost submission.

## 1. Source Of Truth

| Item | Source |
|---|---|
| Official agent entry point | `starter/agent.py` |
| Default scoring agent | `agent/fast_agent.py` |
| Official evaluator wrapper | `tools/eval.py` and `scripts/evaluate.*` |
| Setup scripts | `scripts/setup_local_data.ps1` and `scripts/setup_local_data.sh` |
| Verification scripts | `scripts/verify_submission.ps1` and `scripts/verify_submission.sh` |
| Demo UI | `ui/server.py` and `ui/static/index.html` |
| Devpost text | `docs/devpost_draft.md` |
| Video outline | `docs/demo_video_script.md` |

## 2. Run The Official Score

Windows:

```powershell
.\scripts\verify_submission.ps1 -WithData
.\scripts\evaluate.ps1
```

macOS / Linux:

```bash
sh scripts/verify_submission.sh --with-data
sh scripts/evaluate.sh
```

Expected public-set result for PR #1:

| Metric | Value |
|---|---:|
| HitRate@10 | 1.000000 |
| MRR | 0.729107 |
| MTTC | 1.525000 |
| TechnicalScore | 0.908232 |

If the number is lower, stop and check:

| Check | Why |
|---|---|
| `git status --short` is clean | Avoid mixing local edits into the score. |
| `data/catalog.jsonl` exists | Official scorer needs the full local catalog. |
| `data/public_set.jsonl` exists | Public evaluator needs the 200 sessions. |
| `starter.agent.Agent` imports `agent.fast_agent.Agent` | The evaluator imports this exact path. |

## 3. Run The Demo UI

Windows:

```powershell
.\scripts\demo.ps1 -Fixture
```

macOS / Linux:

```bash
sh scripts/demo.sh --fixture
```

Open:

```text
http://127.0.0.1:8765/
```

If the UI says `Demo fixture catalog: 13 products ready`, that is expected. The
fixture catalog is only for recording a fast browser demo. The official score
uses the downloaded 50,000-product catalog through the evaluator.

## 4. What To Show In The Video

| Shot | Show | Say |
|---|---|---|
| 1 | README / team name | "We are team kpopy demon hunter." |
| 2 | Architecture diagram | "The official evaluator imports a Python backend agent, not the UI." |
| 3 | Method table | "We tested BM25, dense/LTR research, and an offline FastAgent." |
| 4 | Evaluator output | "The current public-set TechnicalScore is 0.908232 with zero paid API calls." |
| 5 | Local UI fixture | "This 13-product UI is just for a quick demo recording." |
| 6 | Devpost draft | "The final submission includes setup, limitations, and team contributions." |

## 5. Package The Submission

Windows:

```powershell
.\scripts\package_submission.ps1
```

macOS / Linux:

```bash
sh scripts/package_submission.sh
```

The script writes:

```text
dist\techjam-track4-submission-<commit>.zip
```

Do not commit `dist/`; it is ignored and generated locally.
