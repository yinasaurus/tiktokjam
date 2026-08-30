# Demo Video Script

Target length: 2 to 4 minutes.

## 1. Opening

Show the repo and explain the task:

> This is a backend conversational shopping copilot for TikTok TechJam 2026
> Track 4. The goal is to find a hidden purchased Amazon product from a frozen
> 50,000-item clothing catalog within 10 turns.

Mention that UI is not part of scoring. The official evaluator imports
`starter.agent.Agent` and scores only returned `parent_asin` IDs.

## 2. Architecture Walkthrough

Show `README.md` and `agent/`.

Cover the four challenge pillars:

- Intent Routing & Hybrid Pipeline: exact phrase, BM25 lexical, dense retrieval,
  fusion, reranking.
- Multi-Turn Scenario Evolution: accumulated slots, declined attributes,
  intent override.
- Dynamic Context Programming: active constraints are rebuilt each turn and the
  workflow adapts between retrieval, clarification, reranking, and fallback.
- Product & Efficiency Metrics: HitRate@10, MRR, MTTC, Efficiency, and
  TechnicalScore.

## 3. Local Setup Proof

Run:

```powershell
.\scripts\setup_local_data.ps1 -DownloadOfficial
python -m pytest tests -q
```

Explain that `data/catalog.jsonl`, `data/public_set.jsonl`, caches, and
`results.json` are local-only and gitignored.

## 4. End-to-End Evaluator

Run:

```powershell
.\scripts\evaluate.ps1
```

Show the printed metrics:

- HitRate@10 as retrieval coverage.
- MRR and top-rank movement as precision.
- MTTC and Efficiency as reduced conversational load.
- Token usage as zero for the offline path.

## 5. Demo Interaction

Run:

```powershell
.\scripts\demo.ps1
```

For a quick UI-only recording pass, use:

```powershell
.\scripts\demo.ps1 -Fixture
```

The fixture mode is not scored; it exists so the visual walkthrough starts
instantly. Use `.\scripts\evaluate.ps1` for the real 50k-catalog score.

Use short prompts:

- `navy cotton t-shirts`
- `black leather boots`
- `I'm looking for running shorts. A key requirement is: cotton.`
- Intent override: start with one product type, then say
  `Actually, ignore my earlier preference. What I need is: leather boots.`
- Boundary: answer a clarification with
  `I don't have a preference for color; please use your judgment.`

Show that the right panel returns ranked product IDs and metadata.

## 6. Close

Summarize:

> The submission is offline, deterministic, and evaluator-compatible. The core
> design prioritizes candidate coverage first, then uses reranking and adaptive
> questions to improve precision and reduce mean turns to conversion.

Avoid showing third-party trademarks beyond what is necessary in the competition
catalog output. For a backend/NLP track, an API/evaluator walkthrough is
acceptable.
