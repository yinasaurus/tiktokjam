# HealthKaki POV Cross-Project Audit

Team: **kpopy demon hunter**

Source repo inspected locally:

```text
X:\01 REPOSITORIES\healthkaki-pov
```

The user originally said `healthkaki pov`; the actual local folder is
`healthkaki-pov`.

## 1. What Was Inspected

| Evidence | Result |
|---|---:|
| Remote branches | 43 |
| Total commits across refs | 856 |
| Current local branch | `main` |
| Current main head | `68963d5 Delete HP AI ADV Testing.pptx` |
| Setup/tooling branch | `origin/chore/dev-setup` at `ec9c87b` |
| Evaluation docs branch | `origin/feature/workflow-v4-eval` at `01c96bb` |
| Optimised workflow branch | `origin/feature/workflow-v5-optimised` at `aa7fcdd` |

Relevant files read:

| File / branch | Useful pattern |
|---|---|
| `README.md` on `main` | Clear setup options, branch strategy, commit message rules, PR checklist. |
| `pyproject.toml` on `main` | Strict pytest markers and explicit test paths. |
| `scripts/setup-dev.sh` | One-command developer bootstrap. |
| `scripts/run-tests.sh` | One-command test runner. |
| `scripts/check-branch-name.sh` | Branch naming convention guard. |
| `scripts/check-protected-branch.sh` | Warning before direct push to protected branches. |
| `origin/feature/workflow-v4-eval:backend_aws/services/README.md` | Evaluation runbook: source of truth, regenerate, run, capture outputs, dashboard. |
| `origin/feature/workflow-v5-optimised:tests/test_parallel_orchestrator.py` | Tests for streaming snapshots, fallback, and final output order. |
| `origin/feature/workflow-v5-optimised:tests/test_parallel_llm_usage.py` | Usage/cost aggregation test. |
| `origin/feature/workflow-v5-optimised:tests/test_parallel_ttft.py` | First visible output should happen early, before slower loading work. |

## 2. What Is Useful For TikTokJam

| HealthKaki pattern | Why it matters here | TikTokJam status |
|---|---|---|
| One-command setup/test flow | Teammates need to run quickly on Windows/macOS/Linux. | Already mostly implemented with paired `.ps1` and `.sh` scripts. |
| Branch naming and protected-branch guard | User requested PR review instead of direct merge to `main`. | Follow manually now; add hook later if time permits. |
| Evaluation runbook | Makes demo/submission reproducible for a new teammate. | Added `docs/evaluation_runbook.md`. |
| Usage/cost tracking | Judges care about feasibility and no paid API dependency. | Current submitted path reports zero tokens and zero paid API calls. |
| Early visible output tests | Demo should show progress fast and not look frozen. | UI health endpoint and fixture demo cover this at a basic level. |
| Fallback tests | A scoring agent must never crash or return invalid output. | `respond()` has a fallback, and tests cover no-repeat asks/min-results. |

## 3. What Is Not Useful For TikTokJam

| HealthKaki idea | Why not copy now |
|---|---|
| Poetry-only setup | TikTokJam already uses plain `requirements.txt` and short scripts; switching now adds deadline risk. |
| Cloud eval capture / S3 dashboard | Our evaluator writes local JSON and the organizer scores a Python agent. |
| LLM workflow orchestration | User explicitly said no paid API calls for this submission. |
| Healthcare schema/prompt logic | Domain is unrelated to shopping search. |
| Large branch/hook rollout | Useful later, but too much process churn before submission. |

## 4. Decision

Do not port HealthKaki code into the scoring agent. Port the process lessons:

| Decision | Action |
|---|---|
| Keep PR-based review | PR #1 remains open against `main`; do not merge without review. |
| Keep paired scripts | Every important Windows command needs a macOS/Linux shell equivalent. |
| Improve teammate handoff | Use `docs/evaluation_runbook.md` for final demo/submission steps. |
| Keep zero paid APIs | Dense/LTR/LLM routes stay research-only unless they beat `0.955300`. |
| Keep measuring honestly | Submit only the best measured method, currently confidence-gated FastAgent. |
