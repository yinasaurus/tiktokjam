# Conversational Shopping Agent

TikTok TechJam 2026, Track 4. Offline multi-turn **search agent** that finds a hidden catalog product within 10 turns.

This is **not** a general chatbot. The customer says what they want; we return 10 product IDs and maybe ask one attribute. Judges score those IDs, not the webpage.

Layout matches the official participant kit. The evaluator imports **`from starter.agent import Agent`**. Do not edit `evaluator/`.

There is **no `.env` file** and **no API key**. Tunables are in `agent/config.py`.

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
python -m evaluator.local_evaluator
```

| Command | What it does |
|---|---|
| `python -m pytest tests -q` | Unit tests (tiny fixture catalog) |
| `python -m ui` | Demo in the browser at **http://127.0.0.1:8765/** — **not scored** |
| `python -m evaluator.local_evaluator` | Official scorer on 200 public sessions → `results.json` |
| `python scripts/chat.py` | Same agent, terminal only |

After pulling code changes, stop the old UI (`Ctrl+C`) and run `python -m ui` again, then click **Reset**.

The kit BM25 starter is `starter/bm25_baseline.py` (Hit@10 0.125). Our system is what `starter/agent.py` exports.

---

## Demo UI

`python -m ui` opens a chat on the left and a **Top 10** product list on the right.

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

M1 wired to the official interface, with a demo UI. Catalog is the frozen 50k `Clothing_Shoes_and_Jewelry` slice. Still to do: Model2Vec in `models/encoder/`, LightGBM rerank, G-2 ablation on the public 200.
