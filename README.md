# Conversational Shopping Agent

Team: **kpopy demon hunter**

[![CI](https://github.com/yinasaurus/tiktokjam/actions/workflows/ci.yml/badge.svg)](https://github.com/yinasaurus/tiktokjam/actions/workflows/ci.yml)

TikTok TechJam 2026, Track 4. Offline multi-turn **search agent** that finds a hidden catalog product within 10 turns.

This is **not** a general chatbot. The customer says what they want; we return 10 product IDs and maybe ask one attribute. Judges score those IDs, not the webpage.

The challenge framing is Shopping Copilot: conversational search and
recommendations over Amazon Reviews 2023-derived catalog data. The source
category is the large `Clothing_Shoes_and_Jewelry` corpus; the competition
ships a frozen 50k product slice plus public evaluation sessions. Use the
participant-kit data for this repo, not a fresh scrape or rewritten catalog.

Competition pillars mapped to this codebase:

- **Intent routing and hybrid pipeline:** exact phrase, lexical BM25, dense
  retrieval, fusion, and reranking in `agent/`.
- **Multi-turn scenario evolution:** `SessionState` accumulates slots, handles
  declined attributes, and supports intent override by superseding constraints.
- **Dynamic context programming:** each turn rebuilds active constraints from
  dialog state and chooses whether to retrieve, ask, rerank, or degrade based on
  budget and candidate quality.
- **Product and efficiency metrics:** local evaluator reports Hit@10, MRR,
  MTTC, Efficiency, TechnicalScore, and zero token usage for the offline path.

Backend flow:

```text
customer turn
    |
    v
template parser -> session state -> question policy
    |                 |              |
    |                 v              v
    |          active constraints   ask_attribute
    v
multi-route retrieval -> fusion -> rerank/fallback -> Top 10 parent_asin
```

Submitted offline architecture:

```text
official evaluator
    |
    v
starter.agent.Agent
    |
    v
FastAgent: parser + SessionState + question policy
    |
    +--> category route
    +--> exact constraint route
    +--> lexical overlap route
    +--> popularity fallback
    |
    v
score/rank candidates -> 10 valid parent_asin + ask_attribute
```

Evaluation loop:

```text
official public_set + frozen catalog
    |
    v
tools/eval.py / scripts/run_ablations.py
    |
    v
overall + buying + browsing + intent_override + boundary metrics
    |
    v
choose best offline method by TechnicalScore, with latency as a gate
```

Metric interpretation for the showcase:

- **Coverage / HitRate@K:** proves the hybrid retrieval stage can keep the
  purchased item inside the candidate set, including boundary and ambiguous
  browsing cases.
- **Precision / MRR / top-rank share:** proves the semantic ranking and
  reranking stage can move the exact purchased item toward rank 1.
- **Efficiency / MTTC:** proves the dialog policy asks useful questions and
  converges before the 10-turn limit.
- **Cost and latency:** prove commercial practicality; this implementation is
  offline and reports zero token usage.

Layout matches the official participant kit. The evaluator imports **`from starter.agent import Agent`**. Do not edit `evaluator/`.

There is **no `.env` file** and **no API key**. Tunables are in `agent/config.py`.
The submission path must not use paid API calls or hosted LLM dependencies.

Official docs: [competition spec](docs/competition_specification.md) · [API contract](docs/agent_api_contract.json) · [submission rules](docs/submission_rules.md) · [PRD](PRD-v2.0-conversational-shopping-agent.md) · [TDD](TDD-v2.0-conversational-shopping-agent.md)

---

## How to start

Python 3.10+ (3.11+ recommended). From the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks the venv:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Unpack the 50k catalog if `data/catalog.jsonl` is missing:

```powershell
python -c "import gzip,shutil; shutil.copyfileobj(gzip.open('catalog.jsonl.gz','rb'), open('data/catalog.jsonl','wb'))"
```

Also copy `data/public_set.jsonl` out of `techjam-participant-kit.zip` if needed. Verify downloads with `SHA256SUMS`.

### Run

```powershell
python -m pytest tests -q
python -m ui
python -m ui --fixture
python -m evaluator.local_evaluator
```

| Command | What it does |
|---|---|
| `python -m pytest tests -q` | Unit tests (tiny fixture catalog) |
| `python -m ui` | Demo in the browser at **http://127.0.0.1:8765/** using the official catalog when present — **not scored** |
| `python -m ui --fixture` | Instant UI smoke/demo mode using the tiny fixture catalog — **not scored** |
| `python -m evaluator.local_evaluator` | Official scorer on 200 public sessions → `results.json` |
| `python scripts/chat.py` | Same agent, terminal only |

After pulling code changes, stop the old UI (`Ctrl+C`) and run `python -m ui` again, then click **Reset**. Use `python -m ui --fixture` when you only need to verify or record the UI flow quickly.

The kit BM25 starter is `starter/bm25_baseline.py` (Hit@10 0.125). Our system is what `starter/agent.py` exports.

### Team production setup

Use the PowerShell helpers when onboarding a teammate or preparing a demo machine:

```powershell
.\scripts\setup_local_data.ps1 -DownloadOfficial
.\scripts\demo.ps1 -Install
.\scripts\demo.ps1 -Fixture
.\scripts\evaluate.ps1
```

macOS/Linux companions:

```bash
sh scripts/setup_local_data.sh --download-official
INSTALL=1 sh scripts/demo.sh
FIXTURE=1 sh scripts/demo.sh
sh scripts/evaluate.sh
```

`setup_local_data.ps1 -DownloadOfficial` downloads only the official participant
kit release assets: `catalog.jsonl.gz`, `techjam-participant-kit.zip`, and
`SHA256SUMS` from
`https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit`.
Without `-DownloadOfficial`, it expects `catalog.jsonl.gz` at the repo root or
in `data/`, and `techjam-participant-kit.zip` at the repo root unless
`data/public_set.jsonl` is already present. The generated
`data/catalog.jsonl`, `data/public_set.jsonl`, `results.json`, `eval_output/`,
and dense caches are gitignored. Always check:

```powershell
git status --short
```

before committing. Local data and evaluator outputs should not be staged.

Optional local speed-up for repeated experiments:

```powershell
$env:TECHJAM_FAST_CACHE = "1"
python scripts\check_acceptance.py --threshold 0.80
```

```bash
TECHJAM_FAST_CACHE=1 sh scripts/evaluate.sh
```

This writes derived indexes under `cache/`, which is gitignored. The submitted
agent does not require the cache; it rebuilds from `data/catalog.jsonl` when the
environment variable is absent.

### Measurement and training commands

```powershell
python scripts/measure_catalog.py --catalog data/catalog.jsonl
python scripts/build_index.py --catalog data/catalog.jsonl
python scripts/run_ablations.py
python scripts/bench_reranker.py --mode heuristic
python scripts/train_ltr.py
python scripts/bench_reranker.py --mode ltr
python tools/eval.py
python tools/eval.py --agent starter.bm25_baseline:Agent
python scripts/check_acceptance.py --threshold 0.80
python scripts/synthetic_customer_gate.py --threshold 0.80 --trials 100
```

The production model plan is:

- Default submission candidate: fast offline evaluator-aligned agent in
  `agent/fast_agent.py`, exported as `starter.agent.Agent`.
- Hybrid research path: `starter.agent.HybridAgent` keeps exact phrase, bm25s,
  dense, fusion, and optional LightGBM experiments available.
- Dense route: vendor a complete Model2Vec static encoder into `models/encoder/`
  only if measured ablations justify it.
- Reranker: train LightGBM LambdaRank and write `models/ltr.txt` only if it
  beats the fast offline method on score and latency.
- Fallback: no paid API calls, no hosted LLM dependency, zero token usage.
- Method selection: compare variants with `scripts/run_ablations.py` and
  timestamped evaluator runs with `tools/eval.py`; submit only the best
  offline method that improves score without unacceptable latency.

CI runs on GitHub Actions with committed fixture data only: unit tests, compile
checks, smoke session, and `scripts/synthetic_customer_gate.py`. The real
release gate is still local because the official 50k catalog and public sessions
are gitignored: `python scripts/check_acceptance.py --threshold 0.80`.

Current measured results:

```text
tools/eval.py --limit 50
overall: HR@10 1.0, MRR 0.661349, MTTC 2.22, TechnicalScore 0.874005
intent_override: HR@10 1.0, MRR 0.90625, MTTC 3.75, TechnicalScore 0.916875

tools/eval.py
overall: HR@10 0.96, MRR 0.681347, MTTC 2.585, TechnicalScore 0.852704
buying: HR@10 0.975, MRR 0.664301, MTTC 1.925, TechnicalScore 0.868290
browsing: HR@10 0.9375, MRR 0.672505, MTTC 2.6375, TechnicalScore 0.837751
intent_override: HR@10 0.966667, MRR 0.755556, MTTC 3.933333, TechnicalScore 0.851334
boundary: HR@10 1.0, MRR 0.665833, MTTC 3.4, TechnicalScore 0.851750
```

Do not commit the 50k catalog, public set, caches, or raw results. The LightGBM
model is expected to be small and may be committed after score and latency checks.

### Submission artifacts

Drafts and checklists live in `docs/`:

- `docs/devpost_draft.md` — project description, tools, APIs, libraries, data,
  limitations, and contribution placeholders.
- `docs/demo_video_script.md` — short walkthrough script for evaluator/API and
  optional UI demo.
- `docs/submission_checklist.md` — public repo, local verification, Devpost, and
  video checklist.

Run a no-data verification pass on any machine:

```powershell
.\scripts\verify_submission.ps1
```

```bash
sh scripts/verify_submission.sh
```

Run the full local verification on a data-bearing machine:

```powershell
.\scripts\verify_submission.ps1 -WithData
```

```bash
sh scripts/verify_submission.sh --with-data
```

Run optional research checks separately:

```powershell
.\scripts\verify_submission.ps1 -WithData -WithResearch
```

```bash
sh scripts/verify_submission.sh --with-data --with-research
```

Build a tracked-file-only zip after `git status --short` is clean:

```powershell
.\scripts\package_submission.ps1
```

```bash
sh scripts/package_submission.sh
```

Print the current live handoff status at any time:

```powershell
python scripts\final_status.py
```

### Do not deploy this to Vercel

Vercel is for serverless functions. It looks for a Flask/FastAPI `app`. Our demo is `python -m ui` — a long-running local server that loads **50,000 products into RAM** and keeps chat state in memory.

Do **not** add this (it will not work):

```toml
[tool.vercel]
entrypoint = "ui.server:Handler"
```

`Handler` is a stdlib HTTP handler, not a Vercel entrypoint. Even if you wrap it, Vercel will not ship `data/catalog.jsonl` (gitignored), will time out on index build, and will forget sessions between requests.

**Demo for teammates / video:** leave it on your machine at http://127.0.0.1:8765/  
**Share a temporary public link:** keep `python -m ui` running, then in another terminal:

```powershell
ngrok http 8765
```

The competition score is still `python -m evaluator.local_evaluator`, not any website.


---

## Demo UI

`python -m ui` opens a chat on the left and a **Top 10** product list on the right. For fast recording setup, use `python -m ui --fixture` or the matching `-Fixture` / `FIXTURE=1` script options; this proves the interface flow without waiting for the 50k-product catalog index.

- Chat is only for questions / short status. Ranked products live in the right panel (not repeated as “Top pick: …” in every bubble).
- Type like a search, not like WhatsApp.

Works:

- `navy cotton t-shirts`
- `black leather boots`
- `I'm looking for running shorts. A key requirement is: cotton.`

Does not (and is not supposed to) work well:

- `mmm idk`
- random slang with no product type

Exam-style edge cases are buy / browse / “actually I want X instead” / “no preference” — not open chit-chat.

---

## Agent contract

```python
from starter.agent import Agent

agent = Agent("data/catalog.jsonl")
agent.reset(session_id, user_profile)
out = agent.respond(session_id, user_message, turn, top_k=10)
```

```python
{
  "message": "Could you share a preferred material?",
  "ask_attribute": "material",   # or null
  "recommendations": [{"parent_asin": "B000..."}],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0}
}
```

`ask_attribute` must be one of: `category`, `material`, `color`, `size`, `style`, `brand`, `budget`, `feature`, `use_case`, `other`, or `null`.

**How they score:** each session has one hidden `parent_asin`. We output 10 IDs. They check if the hidden one is in that list, how high, and on which turn. No UI/UX score.

---

## Layout

```
starter/agent.py           official entry (re-exports Agent)
starter/bm25_baseline.py   kit BM25 starter, kept for comparison
agent/                     retrieval pipeline — does not import evaluator
evaluator/                 official scorer — do not edit
docs/                      official contract and rules
data/                      catalog.jsonl + public_set.jsonl (gitignored)
ui/                        demo webpage only
tests/
scripts/
```

---

## Current status

The current submission default is the offline fast agent exported by
`starter.agent.Agent`. It passes the local official-data acceptance gate at
`TechnicalScore 0.852704` with zero paid API calls. Team setup, evaluation,
fixture CI, demo UI, ablation, reranker benchmark, and LightGBM training scripts
are present. The frozen 50k `Clothing_Shoes_and_Jewelry` catalog remains
local-only and gitignored.

Dense retrieval, Model2Vec vendoring, and `models/ltr.txt` training are optional
research paths now. Enable them for submission only if measured ablations beat
the fast offline default without unacceptable startup or per-turn latency.
