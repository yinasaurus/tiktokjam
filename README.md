# kpopy demon hunter - Shopping Copilot

TikTok TechJam 2026, Track 4: **AI Conversational Search and Recommendations**.

## Project overview

This is a **conversational shopping agent**. A customer sends messages like
`I'm looking for shoes, but I'm still exploring.` Across up to 10 turns the
agent returns a Top 10 list of Amazon `parent_asin` IDs and may ask one
clarification question. The official evaluator scores whether a hidden target
product appears in that list.

**Headline result (public 200 sessions):** TechnicalScore **0.9553**
(HitRate@10 1.000, MRR 0.937, MTTC 2.29). The submitted path
(`starter.agent.Agent` → FastAgent) is offline, CPU-only, and uses **zero
paid API calls**.

## Slide 1: The Simple Idea

| Question | Plain answer |
|---|---|
| What are we building? | A shopping copilot that asks smart questions and ranks products. |
| What does it search? | A frozen 50,000-item Amazon clothing, shoes, and jewelry catalog. |
| What is the goal? | Find the hidden purchased product quickly and place it high in the Top 10. |
| Are we using paid APIs? | No. The submitted path is offline, CPU-only, and uses zero tokens. |
| Team name | `kpopy demon hunter` |

## Slide 2: Why Normal Search Fails

| Customer situation | Why keyword search struggles | What our agent does |
|---|---|---|
| "I need something for work." | Too vague. Many products match. | Ask a clarification question while still returning candidates. |
| "I want black boots." | Hard constraints matter. | Lock onto category and exact constraints. |
| "Actually, ignore that. I need white sneakers." | Old keywords conflict with new intent. | Replace outdated slots instead of appending contradictions. |
| "No preference, use your judgment." | Search cannot learn more from that question. | Move to another attribute and keep ranking. |

## Slide 3: How We Are Scored

| Metric | Easy meaning | Why it matters |
|---|---|---|
| HitRate@10 | Did the correct product appear anywhere in our 10 answers? | Biggest scoring factor. Missing is expensive. |
| MRR | If we hit, how close was the correct product to rank 1? | Better ranking means less shopper effort. |
| MTTC | Mean turns to conversion. Lower is better. | Rewards asking useful questions and converging fast. |
| TechnicalScore | Combined score from HitRate, MRR, and Efficiency. | Main local number we optimize. |

Formula:

```text
TechnicalScore = 0.50 * HitRate@10 + 0.30 * MRR + 0.20 * Efficiency
```

## Slide 4: What We Tried

These are the important method comparisons from the official-style local
evaluator and our current repo status.

| Method | Paid API? | What it does | Expected score | Decision |
|---|---:|---|---:|---|
| Starter BM25 | No | Keyword search, weak/no useful asking | 0.1067 | Reject. Baseline only. |
| Category + memory | No | Remembers turns and uses category narrowing | about 0.25 | Useful but not enough. |
| Ask every turn | No | Always asks valid `ask_attribute` while ranking | about 0.69 | Strong core idea. |
| Exact + lexical fast agent | No | Category, exact constraints, lexical ranking, fallback | 0.852704 | Previous default. |
| Fast agent + confidence gate | No | Adds semicolon-safe constraints, top-50 reranking, position match, and waits for enough evidence before submitting a scored slate | **0.955300** | Submit this by default. |
| Dense / Model2Vec | No | Optional semantic embeddings | Not submitted unless it beats default | Research only. |
| LightGBM LTR | No | Optional learned reranker | Not submitted unless it beats default | Research only. |
| Hosted LLM API | Usually yes | Could rerank or rewrite queries | Not needed | Avoid for cost, credential, and network risk. |

## Slide 4A: What Are We Actually Using?

| Question | Answer |
|---|---|
| Are we using an LLM? | Not in the submitted default. No GPT/Claude/OpenAI/paid API call is required. |
| Are we using BM25? | BM25 means keyword search. We tested BM25-style/hybrid code, but the default is not plain BM25. |
| What is the main method? | Offline ranked retrieval: give every candidate product a score, sort by that score, and return the best 10 IDs. |
| What signals are in the score? | Category, exact disclosed constraints, lexical token overlap, and popularity fallback. |
| Is it machine learning? | The submitted path is mostly deterministic retrieval/ranking. Optional LightGBM training is research-only. |
| Why this choice? | It is faster, cheaper, easier to reproduce, and currently scores better than the heavier research path. |

## Slide 4B: What We Learned From Big Marketplaces

| Platform | What they do | Lesson for us |
|---|---|---|
| Taobao | Qwen/Taobao-style conversational shopping, comparison, and follow-up questions. | Treat shopping as a conversation, not one search box. |
| Lazada | LazzieChat/AI Lazzie gives product suggestions and product links from natural questions. | Keep the assistant helpful and product-grounded. |
| Shopee | Search/recommendation teams and conversational discovery integrations. | Lightweight embeddings and recommendation signals are worth researching, but not at the cost of reliability. |
| Amazon | Rufus/Alexa for Shopping uses query understanding, retrieval, product facts, reviews, and ranking. | Our architecture should be a funnel: parse, retrieve from multiple routes, rerank, return Top 10. |

Detailed research notes in this repo:

```text
docs/research/marketplace_search_patterns.md
docs/research/model_avenues.md
docs/research/healthkaki_pov_lessons.md
docs/evaluation_runbook.md
```

## Slide 4C: 95% TechnicalScore Reality Check

| Metric | Current clean result | Rough target for 95% TechnicalScore |
|---|---:|---:|
| HitRate@10 | 1.000 | about 1.000 |
| MRR | 0.937 | about 0.930+ |
| MTTC | 2.290 | about 2-3 turns is acceptable if MRR improves |

The submitted FastAgent on `main` scores official clean TechnicalScore
`0.955300`. That is above a 95% TechnicalScore target because the agent
waits for enough evidence before submitting recommendations. HitRate was already
maxed out at 1.0; the improvement came from moving many correct products to
rank 1 and raising MRR.

Quick research-branch ablation on 30 sessions:

| Variant | HitRate@10 | MRR | MTTC | TechnicalScore | Decision |
|---|---:|---:|---:|---:|---|
| Hybrid `full` | 0.800 | 0.689815 | 3.933333 | 0.748278 | Below default. |
| Hybrid `no_dense` | 0.766667 | 0.681481 | 4.466667 | 0.718444 | Below default. |
| Hybrid `lexical_only` | 0.100 | 0.041429 | 10.000000 | 0.082429 | Reject. |
| Fast default before rank tie-breaks | 0.960 | 0.681347 | 2.585000 | 0.852704 | Previous best. |
| Fast rank tie-break research | 1.000 | 0.729107 | 1.525000 | 0.908232 | Previous 90% PR candidate. |
| Fast confidence gate | 1.000 | 0.937000 | 2.290000 | 0.955300 | Current default on `main`. |

## Slide 5: Final Architecture

```text
official evaluator or local demo UI
    |
    v
starter.agent.Agent
    |
    v
FastAgent
    |
    +--> parse customer message
    +--> update per-session state
    +--> choose the next question
    |
    v
retrieval routes
    |
    +--> category filter
    +--> exact disclosed constraints
    +--> lexical token overlap
    +--> popularity fallback
    |
    v
rank candidates
    |
    v
if enough evidence: return 10 valid parent_asin IDs + one ask_attribute
else: ask one more question before scoring a slate
```

## Slide 6: What Each Component Means

| Component | File | Student-friendly explanation |
|---|---|---|
| Entry point | `starter/agent.py` | The evaluator imports this. It must always work. |
| Fast agent | `agent/fast_agent.py` | The default submitted brain. Offline and reliable. |
| State | `agent/state.py` | Remembers what the customer already said. |
| Parsing | `agent/parsing.py` | Turns customer text into structured events. |
| Questions | `agent/question.py` | Chooses what attribute to ask next. |
| Catalog tools | `agent/catalog.py` | Loads products and builds local indexes. |
| Research routes | `agent/routes/` | Optional exact, lexical, dense retrieval experiments. |
| Demo UI | `ui/server.py`, `ui/static/index.html` | Local browser demo for video recording, not scored. |
| Evaluation | `tools/eval.py`, `scripts/evaluate.*` | Runs official scoring and reports metrics. |

## Slide 7: Current Measured Result

| Metric | Current value |
|---|---:|
| HitRate@10 | 1.000000 |
| MRR | 0.937000 |
| MTTC | 2.290000 |
| TechnicalScore | **0.955300** |
| Token usage | 0 |
| Paid API calls | 0 |

Internal rule: we only accept a submission method if it reaches
`TechnicalScore >= 0.80` without paid API calls.

## Robustness testing

We tested FastAgent on the 200 public sessions after mechanically rewording
the customer utterances (filler words, clause reordering, punctuation changes)
to check whether the score depended on matching the evaluator's exact phrasing.
On the earlier clean evaluator text, TechnicalScore was 0.852704. On the reworded set
before the parsing change it was 0.467654, a 45.16% gap. The drop came from
order-dependent regex matching in `agent/parsing.py`: clause order and filler
tokens stopped event extraction, even though the content words were the same.
The fix strips a short filler list and searches the full utterance for each
event pattern independently, while leaving the original anchored path in place
for clean input. After the fix, the same reworded set scored 0.844094 (1.01%
gap) and the clean score stayed 0.852704. The later rank tie-break PR lifts
the clean official-style score to 0.908232, and the confidence gate lifts it to
0.955300. On current `main` (post PR #1), the same frozen paraphrase fixture
scores **0.955125** (0.018% gap vs clean 0.9553). Five additional harder paraphrase
styles — synonym substitution, run-on merging, dropping connectives, placing
the override marker mid-utterance, and combining filler with reorder — were
also tested against the committed FastAgent; 5/5 sessions still hit the target
in the Top 10.

## Limitations

Robustness testing was performed against the 200 public sessions only. The
private 800-session evaluation set was not accessible during development, so
while the parsing fix is designed to generalize (it targets structural patterns
like clause order and filler words, not memorized phrasing), its performance
on the private set has not been directly verified.

Given more time, the natural next step is the Hybrid stack already in this
repo (`agent/agent.py`, `agent/routes/`: bm25s, dense Model2Vec, weighted RRF
fusion). We did not submit that path: measured Hybrid ablations scored below
FastAgent once category + exact constraints + top-50 rerank + confidence
gating reached TechnicalScore 0.9553. Hybrid remains a research avenue, not
the official `starter.agent.Agent`.

`models/ltr.txt` is not in the repo. Hybrid `rerank_mode="ltr"` / `"cascade"`
falls back to a linear heuristic when that file is missing. Submitted
FastAgent does not use LightGBM. `models/encoder/` has no Model2Vec weights,
so Hybrid dense retrieval is not production-ready on the 50k catalog.

The confidence gate withholds scored recommendations until two constraints
are known (or turn 4). That raises MRR while increasing MTTC: on the public
200, first-hit never exceeded 4 turns.

## Setup and installation

Pinned dependencies are in `requirements.txt` (`numpy`, `scipy`, `bm25s`,
`model2vec`, `lightgbm`, `pytest`). No PyTorch.

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

.\scripts\setup_local_data.ps1 -DownloadOfficial
.\scripts\verify_submission.ps1 -WithData
.\scripts\demo.ps1 -Fixture
.\scripts\package_submission.ps1
```

If the UI says `Demo fixture catalog: 13 products ready`, that is expected.
Fixture mode loads 13 tiny test products so the demo opens instantly for video
recording. Official evaluation uses the downloaded 50,000-product catalog and
the evaluator, not the fixture UI.

### macOS / Linux

Every important PowerShell script has a matching shell script for teammates.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

sh scripts/setup_local_data.sh --download-official
sh scripts/verify_submission.sh --with-data
sh scripts/demo.sh --fixture
sh scripts/package_submission.sh
```

The same fixture note applies on macOS/Linux: `sh scripts/demo.sh --fixture`
starts the small 13-product recording demo, while `sh scripts/evaluate.sh`
scores the official 50,000-product backend agent.

## Steps to reproduce your results

This is how to see TechnicalScore **0.9553** yourself. The setup commands
above only prepare the environment; these run the official local evaluator.

**Windows**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\scripts\setup_local_data.ps1 -DownloadOfficial
.\scripts\evaluate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
sh scripts/setup_local_data.sh --download-official
sh scripts/evaluate.sh
```

Look in the printed JSON for `"recommended_technical_score": 0.9553`.
That command is `python -m evaluator.local_evaluator` on `data/catalog.jsonl`
and `data/public_set.jsonl` (200 sessions). Optional robustness check:

```powershell
python tests\paraphrase_fixtures.py --reuse-fixture
```

Expected paraphrased TechnicalScore: **0.955125**.

## Slide 10: What Not To Commit

| Local-only item | Why |
|---|---|
| `data/catalog.jsonl` | Official catalog is large and downloaded locally. |
| `data/public_set.jsonl` | Evaluation data should stay local. |
| `catalog.jsonl.gz` | Download artifact, not source code. |
| `techjam-participant-kit.zip` | Download artifact, not source code. |
| `results.json`, `runs/`, `eval_output/` | Machine-generated evaluation outputs. |
| `cache/` | Local index/cache files. |
| `.env`, API keys | Secrets must never be committed. |

## Slide 11: Demo Video Plan

| Step | What to show | Command | What to say |
|---|---|---|---|
| 1 | Repo and team name | Open this README | "We are team kpopy demon hunter, and this is a backend shopping copilot." |
| 2 | Architecture | Show Slide 5 diagram | "The UI is only for recording; the official score comes from `starter.agent.Agent` in the evaluator." |
| 3 | Tests | `python -m pytest tests -q` | "These tests check parsing, ranking, session isolation, and the demo UI files." |
| 4 | Real metrics | `.\scripts\evaluate.ps1` | "This is the official-style local score on the 50,000-product catalog." |
| 5 | Local UI | `.\scripts\demo.ps1 -Fixture` | "The 13-product fixture is a tiny demo catalog, not the scored catalog." |
| 6 | No paid API | Show zero token / no API-key section | "The submitted path is offline, no hosted LLM, no paid API, zero token usage." |

## Slide 12: Final Checklist

| Status | Item |
|---|---|
| Done | Offline agent exported as `starter.agent.Agent`. |
| Done | No paid API calls required. |
| Done | Windows `.ps1` and macOS/Linux `.sh` scripts exist. |
| Done | Package scripts write both the submission zip and a `.zip.sha256` checksum. |
| Done | Simple local UI exists for demo recording. |
| Done | CI tests and synthetic fixture gate run on GitHub Actions. |
| Done | Current expected TechnicalScore is 0.955300, above 0.80 and above 95%. |
| Todo | Fill individual member names and contribution split (see Team member contributions). |
| Todo | Review and merge any open final PR before final packaging from `main`. |
| Todo | Record and upload the public YouTube demo. |
| Todo | Paste Devpost draft and submit before the deadline. |

## Team member contributions

Fill this in before Devpost submit. Do not invent names.

| Member | Contributions |
|---|---|
| [Name] | [fill in] |
| [Name] | [fill in] |
| [Name] | [fill in] |

Team name: `kpopy demon hunter`.

## Key Links

| Link | URL |
|---|---|
| Repository | https://github.com/yinasaurus/tiktokjam |
| Main PostPlan | https://mj4gkxs69b24.postplan.dev |
| Status PostPlan | https://pbexoc8bktvw.postplan.dev |
| Official participant repo | https://github.com/TechJam2026/techjam-conversational-search |
| Participant kit release | https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit |
