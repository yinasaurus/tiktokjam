# Devpost Draft: Shopping Copilot

Team: **kpopy demon hunter**

Repository: https://github.com/yinasaurus/tiktokjam

Main PostPlan: https://mj4gkxs69b24.postplan.dev

Status PostPlan: https://pbexoc8bktvw.postplan.dev

## 1. Project Summary

| Question | Answer |
|---|---|
| What did we build? | An offline conversational shopping agent. |
| What problem does it solve? | It helps a shopper find the right product even when the shopper is vague, changes their mind, or gives constraints over multiple turns. |
| What does it output? | A ranked Top 10 list of valid Amazon `parent_asin` product IDs and one optional clarification question. |
| Does it require paid APIs? | No. The submitted path is offline, CPU-only, and uses zero token calls. |

## 2. Problem

Normal e-commerce search depends heavily on keywords. That breaks when the
customer says something vague like "I need something comfortable for work", or
when they change their mind halfway through the conversation.

The challenge asks us to build a backend shopping copilot that can:

| Challenge behavior | What it means | Our approach |
|---|---|---|
| Buying | Customer has hard requirements. | Use category and exact constraints early. |
| Browsing | Customer is still exploring. | Ask useful clarification questions while still ranking products. |
| Intent override | Customer says to ignore earlier preference. | Replace old intent instead of mixing old and new constraints. |
| Boundary | Customer has no preference for an attribute. | Move on to another attribute and keep recommending. |

## 3. Architecture

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
    +--> choose next ask_attribute
    |
    v
category + exact + lexical + popularity routes
    |
    v
rank candidates
    |
    v
return 10 valid parent_asin IDs + one question
```

## 4. Method Comparison

| Method | Paid API? | What it does | Expected score | Decision |
|---|---:|---|---:|---|
| Starter BM25 | No | Basic keyword search. | 0.1067 | Baseline only. |
| Category + memory | No | Remembers earlier turns and category. | about 0.25 | Useful foundation. |
| Ask every turn | No | Always asks a valid attribute question while recommending. | about 0.69 | Core idea. |
| Fast exact + lexical agent | No | Uses category, exact constraints, lexical ranking, and fallback. | 0.852704 | Previous default. |
| Fast + rank tie-breaks | No | Adds semicolon-safe constraints, top-50 reranking, position matching, and popularity tie-breaks. | **0.908232** | **PR candidate.** |
| Dense embeddings | No | Optional semantic search. | Must beat default first. | Research only. |
| LightGBM reranker | No | Optional learned ranking model. | Must beat default first. | Research only. |
| Hosted LLM API | Usually yes | External model calls for rewriting/ranking. | Not needed. | Avoided. |

## 5. Marketplace Research

We looked at Taobao, Lazada, Shopee, and Amazon to understand how mature
shopping platforms tackle the same issue.

| Platform | Useful lesson |
|---|---|
| Taobao | Shopping assistants ask follow-up questions and support comparison-style discovery. |
| Lazada | Conversational product suggestions should stay grounded in product facts and links. |
| Shopee | Recommendation/search systems use matching, ranking, and lightweight representation learning. |
| Amazon | The closest match to this challenge is a retrieval funnel: query understanding, candidate retrieval, ranking, and conversational guidance. |

We copied the safe offline parts of this pattern: state tracking, clarification,
hybrid-style retrieval signals, ranked Top 10 output, and fallback behavior. We
did not copy cloud-only or paid-API dependencies.

We also reviewed our earlier HealthKaki POV project for process lessons. The
useful parts were teammate setup scripts, evaluation runbooks, PR review
discipline, usage tracking, and fallback tests. We did not copy its healthcare
domain logic or cloud/LLM workflow code into this shopping agent.

## 6. Current Measured Result

| Metric | Value | Meaning |
|---|---:|---|
| HitRate@10 | 1.000000 | The correct product appears in the Top 10 for every public session. |
| MRR | 0.729107 | The correct product is usually ranked high, but rank 1 is still the main gap. |
| MTTC | 1.525000 | The agent usually converts in about 1 to 2 turns. |
| TechnicalScore | **0.908232** | Above our internal 0.80 acceptance gate. |
| Token usage | 0 | No paid API calls in the submitted path. |

## 7. Tools, Libraries, APIs

| Category | Used |
|---|---|
| Language | Python 3.11+ |
| Libraries | `numpy`, `scipy`, `bm25s`, `model2vec`, `lightgbm`, `pytest` |
| APIs | No hosted API required for submitted path |
| UI | Standard-library local HTTP server and static HTML |
| Development | VSCode / terminal-friendly scripts |

## 8. Dataset and Assets

| Asset | How we use it |
|---|---|
| Frozen 50,000-product catalog | Local scoring catalog. |
| 200 public sessions | Local evaluation and ablation testing. |
| 800 private sessions | Held by organizer for final evaluation. |
| Amazon Reviews 2023 lineage | Source of the organizer-provided catalog slice. |

We do not reconstruct the full upstream Amazon Reviews 2023 dataset. We use the
official participant kit assets only. Local data files are gitignored and are
not committed.

## 9. Reproducibility

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\scripts\setup_local_data.ps1 -DownloadOfficial
.\scripts\verify_submission.ps1 -WithData
.\scripts\demo.ps1 -Fixture
```

macOS / Linux:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
sh scripts/setup_local_data.sh --download-official
sh scripts/verify_submission.sh --with-data
sh scripts/demo.sh --fixture
```

## 10. Limitations

| Limitation | What we would improve |
|---|---|
| Text-only catalog | Add multimodal image/product understanding in a real system. |
| Frozen catalog | Add catalog update handling for production. |
| Evaluator-specific templates | Keep semantic fallback and avoid relying only on exact strings. |
| Demo UI is simple | Build a richer product-facing UI after the backend competition. |
| Optional dense/LTR paths are research-only | Submit them only if measured score and latency improve. |

## 11. Team Contributions

Team name: **kpopy demon hunter**

Fill individual names and contribution split before final Devpost submission:

| Member | Contribution |
|---|---|
| Team member 1 | _Fill in_ |
| Team member 2 | _Fill in_ |
| Team member 3 | _Fill in_ |
| Team member 4 | _Fill in_ |
