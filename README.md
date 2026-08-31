# kpopy demon hunter - Shopping Copilot

TikTok TechJam 2026, Track 4: **AI Conversational Search and Recommendations**.

This project is a backend shopping agent. A customer sends messages like
`I'm looking for shoes, but I'm still exploring.` The agent must return up to
10 Amazon product IDs and may ask one useful question. The evaluator checks
whether the hidden target product appears in the returned Top 10 within 10 turns.

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
| Exact + lexical fast agent | No | Category, exact constraints, lexical ranking, fallback | **0.852704** | Submit this by default. |
| Dense / Model2Vec | No | Optional semantic embeddings | Not submitted unless it beats default | Research only. |
| LightGBM LTR | No | Optional learned reranker | Not submitted unless it beats default | Research only. |
| Hosted LLM API | Usually yes | Could rerank or rewrite queries | Not needed | Avoid for cost, credential, and network risk. |

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
return 10 valid parent_asin IDs + one ask_attribute
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
| HitRate@10 | 0.960000 |
| MRR | 0.681347 |
| MTTC | 2.585000 |
| TechnicalScore | **0.852704** |
| Token usage | 0 |
| Paid API calls | 0 |

Internal rule: we only accept a submission method if it reaches
`TechnicalScore >= 0.80` without paid API calls.

## Robustness testing

We tested FastAgent on the 200 public sessions after mechanically rewording
the customer utterances (filler words, clause reordering, punctuation changes)
to check whether the score depended on matching the evaluator's exact phrasing.
On clean evaluator text, TechnicalScore was 0.852704. On the reworded set
before the parsing change it was 0.467654, a 45.16% gap. The drop came from
order-dependent regex matching in `agent/parsing.py`: clause order and filler
tokens stopped event extraction, even though the content words were the same.
The fix strips a short filler list and searches the full utterance for each
event pattern independently, while leaving the original anchored path in place
for clean input. After the fix, the same reworded set scored 0.844094 (1.01%
gap) and the clean score stayed 0.852704. Five additional harder paraphrase
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

## Slide 8: How To Run On Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

.\scripts\setup_local_data.ps1 -DownloadOfficial
.\scripts\verify_submission.ps1 -WithData
.\scripts\demo.ps1 -Fixture
.\scripts\package_submission.ps1
```

## Slide 9: How To Run On macOS / Linux

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

| Step | What to show | Command |
|---|---|---|
| 1 | Repo and team name | Open this README |
| 2 | Architecture | Show Slide 5 diagram |
| 3 | Tests | `python -m pytest tests -q` |
| 4 | Real metrics | `.\scripts\evaluate.ps1` |
| 5 | Local UI | `.\scripts\demo.ps1 -Fixture` |
| 6 | No paid API | Show zero token / no API-key section |

## Slide 12: Final Checklist

| Status | Item |
|---|---|
| Done | Offline agent exported as `starter.agent.Agent`. |
| Done | No paid API calls required. |
| Done | Windows `.ps1` and macOS/Linux `.sh` scripts exist. |
| Done | Simple local UI exists for demo recording. |
| Done | CI tests and synthetic fixture gate run on GitHub Actions. |
| Done | Current expected TechnicalScore is above 0.80. |
| Todo | Fill individual member names and contribution split. |
| Todo | Record and upload the public YouTube demo. |
| Todo | Paste Devpost draft and submit before the deadline. |

## Key Links

| Link | URL |
|---|---|
| Repository | https://github.com/yinasaurus/tiktokjam |
| Main PostPlan | https://mj4gkxs69b24.postplan.dev |
| Status PostPlan | https://pbexoc8bktvw.postplan.dev |
| Official participant repo | https://github.com/TechJam2026/techjam-conversational-search |
| Participant kit release | https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit |
