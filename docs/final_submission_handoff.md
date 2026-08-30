# Final Submission Handoff

Date: 2026-08-31 Singapore time.

## Current Submit Commit

Use the latest pushed `main`. Verify before packaging:

```powershell
git pull origin main
git status --short
git log -1 --oneline
```

Latest checked commit when this handoff section was last updated:

```text
4133c16 docs: refresh final package reference
```

Public GitHub repository:

```text
https://github.com/yinasaurus/tiktokjam
```

Shared PostPlan:

```text
https://mj4gkxs69b24.postplan.dev
```

## Required Final Commands

On the data-bearing Windows machine:

```powershell
git pull origin main
git status --short
.\scripts\verify_submission.ps1 -WithData
.\scripts\package_submission.ps1
```

On macOS/Linux:

```bash
git pull origin main
git status --short
sh scripts/verify_submission.sh --with-data
sh scripts/package_submission.sh
```

Expected official-data acceptance score:

```text
HitRate@10: 0.960000
MRR: 0.681347
MTTC: 2.585000
TechnicalScore: 0.852704
```

The package script writes a commit-specific zip:

```text
dist\techjam-track4-submission-<commit>.zip
```

Use the filename printed by `scripts/package_submission.ps1` or
`scripts/package_submission.sh` after the final `git pull`.

## Demo Recording

Fast UI flow:

```powershell
.\scripts\demo.ps1 -Fixture
```

Use the preset buttons in the chat panel for a quick walkthrough of buying,
browsing, override, and boundary-style messages. For override, click `Reset`,
then `Override 1`, then `Override 2`.

Official-catalog UI flow:

```powershell
.\scripts\demo.ps1
```

Real score output for the video:

```powershell
.\scripts\evaluate.ps1
```

Use `docs/demo_video_script.md` as the voiceover outline.

## Devpost Paste Order

1. Paste `docs/devpost_draft.md`.
2. Fill team names and contribution split.
3. Add the public GitHub URL.
4. Add the public YouTube demo URL.
5. Include the measured score block above.
6. State clearly: no paid API calls, no hosted LLM dependency, zero token usage.

## Do Not Submit

- `data/catalog.jsonl`
- `data/public_set.jsonl`
- `catalog.jsonl.gz`
- `techjam-participant-kit.zip`
- `results.json`
- `runs/`
- `eval_output/`
- `cache/`
- `.env` or credentials
