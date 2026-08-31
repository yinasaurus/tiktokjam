# Technical Report

Team: **kpopy demon hunter**

## 1. One-Sentence Summary

We built an offline shopping copilot that asks useful clarification questions and
returns ranked Amazon product IDs, without paid APIs or hosted model calls.

## 2. Who This Helps

| User | Problem | How our system helps |
|---|---|---|
| Vague shopper | "I need something for work" returns too many products. | Ask a question and keep a broad but ranked candidate set. |
| Decisive shopper | "I need black leather boots" has hard constraints. | Lock onto category and exact constraints quickly. |
| Shopper who changes mind | Old and new preferences can conflict. | Replace older slots when intent override happens. |
| Hackathon judge | Needs a reproducible backend result. | Run one command and get official evaluator metrics. |

## 3. Architecture

```text
official evaluator / demo UI
    |
    v
starter.agent.Agent
    |
    v
FastAgent
    |
    +--> parse message
    +--> update session memory
    +--> choose ask_attribute
    |
    v
category + exact + lexical + popularity routes
    |
    v
return 10 valid parent_asin IDs
```

| Component | File | Purpose |
|---|---|---|
| Official entrypoint | `starter/agent.py` | The evaluator imports this. |
| Submitted agent | `agent/fast_agent.py` | Offline scoring path. |
| Session memory | `agent/state.py` | Tracks constraints and intent changes. |
| Question policy | `agent/question.py` | Chooses the next attribute to ask. |
| Research path | `agent/routes/`, `agent/rerank.py` | Dense/LTR experiments only if they beat default. |
| Demo UI | `ui/` | Local recording aid, not part of scoring. |

## 4. Model Choice

| Option | Cost | Risk | Current decision |
|---|---:|---|---|
| Fast offline exact + lexical agent | $0 | Low | Submitted default. |
| Model2Vec dense retrieval | $0 | Medium startup/artifact complexity | Research only. |
| LightGBM LambdaRank | $0 | Needs training and can overfit | Research only. |
| Hosted LLM API | Paid/credentialed | Network, cost, private credential exposure | Not used. |

The default submission path has no hosted model, no paid API, no external vector
database, no committed private credential, and zero token usage.

## 5. Method Comparison

| Method | What changed | Expected TechnicalScore | Lesson |
|---|---|---:|---|
| Starter BM25 | Keyword search only | 0.1067 | Too weak because it does not ask well. |
| Category + memory | Remember turns and category | about 0.25 | Memory matters. |
| Valid question each turn | Ask while recommending | about 0.69 | Clarification is the biggest win. |
| Fast exact + lexical | Add exact constraints and fallback | 0.852704 | Previous best. |
| Fast + rank tie-breaks | Semicolon-safe constraints, top-50 reranking, position matching, popularity tie-breaks | **0.908232** | Best current PR candidate. |
| Dense/LTR research | Add semantic/model ranking | Must beat 0.908232 | Only ship if measured better. |

## 6. Current Public-Set Result

Measured with the official-style local evaluator on 200 public sessions.

| Scope | HitRate@10 | MRR | MTTC | TechnicalScore |
|---|---:|---:|---:|---:|
| Overall | 1.000000 | 0.729107 | 1.525000 | 0.908232 |
| Buying | 1.000000 | 0.756285 | 1.075000 | 0.925385 |
| Browsing | 1.000000 | 0.649648 | 1.212500 | 0.890644 |
| Intent Override | 1.000000 | 0.925000 | 3.600000 | 0.925500 |
| Boundary | 1.000000 | 0.559683 | 1.400000 | 0.859905 |

## 7. Cost, Latency, Tokens

| Item | Value |
|---|---|
| Paid API calls | 0 |
| Token usage | 0 |
| Network required for scoring | No |
| GPU required | No |
| External vector DB | No |
| Official data committed | No |

## 8. What Generalises

| Strength | Why it matters in production |
|---|---|
| Asking useful questions | Real shoppers often do not know the perfect keyword. |
| Session memory | A copilot must remember what the shopper already said. |
| Intent override handling | Real users change their minds. |
| Offline fallback | The system still works if network/model services fail. |

## 9. Limitations

| Limitation | Future improvement |
|---|---|
| Text-only product data | Add image/multimodal understanding after the hackathon. |
| Frozen catalog | Add catalog update and index refresh flow. |
| English-only assumptions | Add multilingual parsing and retrieval. |
| Simple demo UI | Build a richer product UI for real shoppers. |
| Exact phrase signal is evaluator-aligned | Keep semantic fallback so the architecture survives more natural phrasing. |

## 10. Final Submission Position

Submit the fast offline agent unless a fresh full public-set ablation beats
`TechnicalScore 0.908232` with acceptable latency and no paid API calls.
