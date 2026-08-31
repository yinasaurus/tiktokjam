# Demo Video Script

Target length: 2 to 4 minutes.

Use `docs/youtube_description.md` for the upload title and description.

## Slide Order

| Time | What to show | What to say |
|---|---|---|
| 0:00 | README title | "We are team kpopy demon hunter. This is our Shopping Copilot for TikTok TechJam Track 4." |
| 0:15 | Simple idea table | "The backend agent must find a hidden product from a 50,000-item catalog within 10 turns." |
| 0:35 | Why normal search fails table | "Customers can be vague, high-intent, or change their mind. The agent needs memory and good questions." |
| 0:55 | Method comparison table | "We compared approaches and chose the best measured offline method, not a paid API." |
| 1:20 | Architecture diagram | "The evaluator calls starter.agent.Agent. Our FastAgent parses messages, updates state, asks a question, ranks products, and returns 10 IDs." |
| 1:55 | Metrics table | "The current expected TechnicalScore is 0.902564, above our 0.80 gate and above 90%, with zero token usage." |
| 2:20 | Terminal or CI | "Tests, compile checks, repository hygiene, and CI are green." |
| 2:40 | Local UI | "The UI is just for demonstration. The backend API is what the challenge scores." |
| 3:10 | Closing | "The solution is reproducible, offline, no paid API calls, with Windows and macOS/Linux setup scripts." |

## Commands To Show

Windows:

```powershell
python -m pytest tests -q
.\scripts\evaluate.ps1
.\scripts\demo.ps1 -Fixture
```

macOS / Linux equivalent:

```bash
python -m pytest tests -q
sh scripts/verify_submission.sh --with-data
sh scripts/demo.sh --fixture
```

## One-Minute Architecture Explanation

```text
customer message
  -> starter.agent.Agent
  -> FastAgent
  -> parse message and update memory
  -> ask one useful attribute
  -> rank using category, exact constraints, lexical overlap, and fallback
  -> return 10 product IDs
```

## Important Lines To Mention

- No paid APIs.
- No hosted LLM dependency.
- Zero token usage during scoring.
- Official data stays local and gitignored.
- UI is only for video; evaluator scores backend product IDs.
- We only submit methods that beat `TechnicalScore >= 0.80`.
