# Final Submission Handoff

Date: 2026-08-31 Singapore time.

Team: **kpopy demon hunter**

## Current Review PR

Current best code is in an open review PR, not merged to `main` yet.

```text
PR: https://github.com/yinasaurus/tiktokjam/pull/1
Branch: research/dense-ltr-marketplaces
Latest PR HEAD: use the current GitHub PR head or run `python scripts\final_status.py`
Score-changing code commit: 862e22d Improve FastAgent precision with confidence gate
Reviewer requested: @yinasaurus
Status: open, non-draft, CI passed
```

Do not merge this PR until the team has reviewed it. After review, merge PR #1
to `main`, then run the final commands below from `main`.

Before the PR is merged, reviewers can inspect the exact branch:

```powershell
git fetch origin
git switch research/dense-ltr-marketplaces
git pull --ff-only origin research/dense-ltr-marketplaces
python scripts\final_status.py
```

## Current Submit Commit

After PR #1 is reviewed and merged, use the latest pushed `main`. Verify before
packaging:

```powershell
git switch main
git pull --ff-only origin main
git status --short
git log -1 --oneline
python scripts\final_status.py
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
git switch main
git pull --ff-only origin main
git status --short
.\scripts\verify_submission.ps1 -WithData
.\scripts\package_submission.ps1
```

On macOS/Linux:

```bash
git switch main
git pull --ff-only origin main
git status --short
sh scripts/verify_submission.sh --with-data
sh scripts/package_submission.sh
```

Expected official-data acceptance score:

```text
HitRate@10: 1.000000
MRR: 0.937000
MTTC: 2.290000
TechnicalScore: 0.955300
```

The package script writes a commit-specific zip and a matching SHA256 file:

```text
dist\techjam-track4-submission-<commit>.zip
dist\techjam-track4-submission-<commit>.zip.sha256
```

Use the filename printed by `scripts/package_submission.ps1` or
`scripts/package_submission.sh` after the final `git pull`. Keep the checksum
beside the zip so the submitted artifact can be verified later.

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
Use `docs/youtube_description.md` as the upload title/description template.

## Devpost Paste Order

Devpost requires a logged-in browser session. Paste manually from the final
merged repo state.

1. Paste `docs/devpost_draft.md`.
2. Fill individual names and contribution split.
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
