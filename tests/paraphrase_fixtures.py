"""Mechanical, meaning-preserving paraphrases of evaluator customer utterances.

Does not change FastAgent or evaluator/. Used only to measure robustness.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FILLERS = frozenset({"just", "really", "also"})
SOFTENERS = (
    ("prefix", "um, "),
    ("suffix", " I guess"),
    ("suffix", " if that makes sense"),
)

_BUYING = re.compile(
    r"^I'm looking for (?P<category>.+?)\. A key requirement is: (?P<constraint>.+)\.$"
)
_BROWSE = re.compile(
    r"^I'm looking for (?P<category>.+?), but I'm still exploring\.$"
)
_OVERRIDE = re.compile(
    r"^Actually, ignore my earlier preference\. What I need is: (?P<new>.+)\.$"
)
_DISCLOSE = re.compile(r"^For that, what matters is: (?P<values>.+)\.$")
_NO_PREF = re.compile(
    r"^I don't have a preference for (?P<attr>.+?); please use your judgment\.$"
)
_EXHAUST = re.compile(
    r"^I don't have an additional preference for (?P<attr>.+)\.$"
)
_OPEN_OVERRIDE = re.compile(r"^I'm looking for (?P<category>.+?)\. (?P<old>.+)$")
_REBUKE = "Those options are not quite right yet. Ask me about one specific attribute."
_FOR_CLAUSE = re.compile(
    r"^(?P<main>.+?) for (?P<pp>[^,.:;]+)$",
    flags=re.IGNORECASE,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "paraphrased_public_200.json"
HARDER_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "harder_paraphrases.json"

# Supplementary set only. Do not feed these through write_fixture() / the
# public-200 file — that fixture must stay frozen for the 45.16% → 1.01% result.
HARDER_CASES = [
    {
        "id": 1,
        "style": "synonym_swap",
        "sample_id": "public_0005",
        "replace_turn": 1,
        "original": (
            "I'm looking for Outdoor & Work Snow & Cold Weather. "
            "A key requirement is: leather."
        ),
        "utterance": (
            "I'm looking for Outdoor & Work Snow & Cold Weather. "
            "A key requirement is: genuine leather material."
        ),
    },
    {
        "id": 2,
        "style": "run_on_merge",
        "sample_id": "public_0001",
        "replace_turn": 1,
        "original": (
            "I'm looking for Jewelry Necklaces. "
            "A key requirement is: Material:alloy."
        ),
        "utterance": (
            "I'm looking for Jewelry Necklaces and a key requirement is Material:alloy."
        ),
    },
    {
        "id": 3,
        "style": "terse_drop_connectives",
        "sample_id": "public_0001",
        "replace_turn": 1,
        "original": (
            "I'm looking for Jewelry Necklaces. "
            "A key requirement is: Material:alloy."
        ),
        "utterance": "Jewelry Necklaces, material alloy",
    },
    {
        "id": 4,
        "style": "mid_utterance_override",
        "sample_id": "public_0002",
        "replace_turn": 3,
        "original": "Actually, ignore my earlier preference. What I need is: leather.",
        "utterance": (
            "What I need is leather, actually scratch my last preference, so leather"
        ),
    },
    {
        "id": 5,
        "style": "filler_plus_reorder",
        "sample_id": "public_0006",
        "replace_turn": 1,
        "original": "I'm looking for Basketball Men, but I'm still exploring.",
        "utterance": "um, I'm still exploring, looking for Basketball Men I guess",
    },
]


def _seed(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def _drop_filler_in(text: str) -> str:
    tokens = text.split()
    for i, tok in enumerate(tokens):
        bare = tok.lower().strip(".,;:!?")
        if bare in FILLERS:
            return " ".join(tokens[:i] + tokens[i + 1 :])
    return text


def drop_filler(text: str) -> str:
    """Drop one filler-safe token from the wrapper, never from a ': ' payload."""
    if ": " in text:
        head, tail = text.rsplit(": ", 1)
        return _drop_filler_in(head) + ": " + tail
    return _drop_filler_in(text)


def add_softener(text: str) -> str:
    kind, phrase = SOFTENERS[_seed(text) % len(SOFTENERS)]
    if kind == "prefix":
        return phrase + text
    return text + phrase


def swap_punctuation(text: str) -> str:
    if text.endswith("."):
        return text[:-1]
    if text.endswith(","):
        return text
    return text + ","


def reorder_clause(text: str) -> str:
    raw = (text or "").strip()
    match = _BUYING.match(raw)
    if match:
        return (
            f"A key requirement is: {match.group('constraint')}. "
            f"I'm looking for {match.group('category')}."
        )
    match = _BROWSE.match(raw)
    if match:
        return f"I'm still exploring, but I'm looking for {match.group('category')}."
    match = _OVERRIDE.match(raw)
    if match:
        return (
            f"What I need is: {match.group('new')}. "
            f"Actually, ignore my earlier preference."
        )
    match = _DISCLOSE.match(raw)
    if match:
        return f"What matters is: {match.group('values')}, for that."
    match = _NO_PREF.match(raw)
    if match:
        return (
            f"Please use your judgment; I don't have a preference for "
            f"{match.group('attr')}."
        )
    if raw == _REBUKE:
        return "Ask me about one specific attribute. Those options are not quite right yet."
    match = _EXHAUST.match(raw)
    if match:
        return raw
    match = _OPEN_OVERRIDE.match(raw)
    if match:
        old = match.group("old").rstrip(".")
        return f"{old}. I'm looking for {match.group('category')}."
    if " looking for " not in raw.lower():
        stripped = raw[:-1] if raw.endswith(".") else raw
        match = _FOR_CLAUSE.match(stripped)
        if match:
            main = match.group("main").strip()
            pp = match.group("pp").strip()
            if main and pp:
                rebuilt = f"for {pp}, {main}"
                return rebuilt + ("." if raw.endswith(".") else "")
    return raw


def paraphrase(text: str) -> str:
    """Apply the four mechanical transforms in a fixed, deterministic order."""
    out = reorder_clause(text)
    out = drop_filler(out)
    out = swap_punctuation(out)
    out = add_softener(out)
    return out


class RecordingAgent:
    """Forwards original text to FastAgent; records original + paraphrase."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.sessions: list[dict] = []
        self._current: dict | None = None

    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        self._current = {"turns": []}
        self.sessions.append(self._current)
        self.inner.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int = 10) -> dict:
        original = user_message or ""
        if self._current is not None:
            self._current["turns"].append(
                {
                    "turn": int(turn),
                    "original": original,
                    "paraphrased": paraphrase(original),
                }
            )
        return self.inner.respond(session_id, original, turn, top_k)


class ParaphraseAgent:
    """Same FastAgent, but the customer text is paraphrased before respond()."""

    def __init__(self, inner) -> None:
        self.inner = inner

    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        self.inner.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int = 10) -> dict:
        return self.inner.respond(session_id, paraphrase(user_message or ""), turn, top_k)


def write_fixture(samples: list[dict], recorded: list[dict], path: Path = FIXTURE_PATH) -> dict:
    sessions = []
    for sample, rec in zip(samples, recorded, strict=True):
        sessions.append(
            {
                "sample_id": sample.get("sample_id"),
                "scenario_type": sample.get("scenario_type"),
                "ground_truth": sample.get("ground_truth", {}).get("parent_asin"),
                "turns": rec["turns"],
            }
        )
    payload = {
        "description": (
            "Mechanical paraphrases of the evaluator-generated customer utterances "
            "for the public 200. Ground-truth ASINs are unchanged."
        ),
        "transforms": [
            "reorder_clause",
            "drop_filler",
            "swap_punctuation",
            "add_softener",
        ],
        "session_count": len(sessions),
        "utterance_count": sum(len(s["turns"]) for s in sessions),
        "sessions": sessions,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def metrics(result: dict) -> dict[str, float]:
    return {
        "hit_rate_at_10": float(result["hit_rate_at_10"]),
        "mrr": float(result["mrr"]),
        "mttc": float(result["mttc"]),
        "technical_score": float(result["recommended_technical_score"]),
    }


def write_harder_fixture(path: Path = HARDER_FIXTURE_PATH) -> None:
    payload = {
        "description": (
            "Supplementary harder paraphrases. Separate from "
            "paraphrased_public_200.json, which must stay frozen."
        ),
        "cases": HARDER_CASES,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def evaluate_with_turn_swap(
    agent,
    sample: dict,
    catalog_ids: set,
    categories: dict,
    products: dict,
    replace_turn: int,
    harder_text: str,
) -> dict:
    """Official evaluate() loop for one sample, with one customer turn swapped."""
    from evaluator.local_evaluator import (
        MAX_TURNS,
        TOP_K,
        coarse_category,
        customer_reply,
        initial_message,
        materialize_hidden_fields,
        normalize_recommendations,
    )

    session_id = f"harder_{sample['sample_id']}_{replace_turn}"
    agent.reset(session_id, sample["user_profile"])
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}
    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    user_message = initial_message(
        effective, coarse_category(categories.get(target, [])), disclosed
    )
    hit_turn: int | None = None
    best_rank: int | None = None
    used: list[str] = []
    for turn in range(1, MAX_TURNS + 1):
        if turn == replace_turn:
            user_message = harder_text
        used.append(user_message)
        try:
            response = agent.respond(session_id, user_message, turn, TOP_K)
        except Exception:
            response = {"message": "", "ask_attribute": None, "recommendations": []}
        if not isinstance(response, dict) or not isinstance(response.get("message"), str):
            response = {"message": "", "ask_attribute": None, "recommendations": []}
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        if override_applied and target in ranked:
            best_rank = ranked.index(target) + 1
            hit_turn = turn
            break
        if turn == MAX_TURNS:
            break
        override = effective.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            user_message = str(
                override.get("message", "Actually, please ignore my earlier preference.")
            )
        else:
            user_message, boundary_used = customer_reply(
                effective, response.get("ask_attribute"), disclosed, boundary_used
            )
    return {
        "sample_id": sample["sample_id"],
        "hit": hit_turn is not None,
        "first_hit_turn": hit_turn,
        "best_rank": best_rank,
        "utterances": used,
    }


def run_harder_cases() -> list[dict]:
    from evaluator.local_evaluator import catalog_index, load_jsonl
    from starter.agent import Agent

    write_harder_fixture()
    samples = {row["sample_id"]: row for row in load_jsonl(ROOT / "data" / "public_set.jsonl")}
    catalog_ids, categories, products = catalog_index(ROOT / "data" / "catalog.jsonl")
    agent = Agent(ROOT / "data" / "catalog.jsonl")
    results = []
    for case in HARDER_CASES:
        sample = samples[case["sample_id"]]
        outcome = evaluate_with_turn_swap(
            agent,
            sample,
            catalog_ids,
            categories,
            products,
            case["replace_turn"],
            case["utterance"],
        )
        row = {
            "id": case["id"],
            "style": case["style"],
            "utterance": case["utterance"],
            "hit": outcome["hit"],
            "first_hit_turn": outcome["first_hit_turn"],
            "best_rank": outcome["best_rank"],
        }
        results.append(row)
        print(json.dumps(row), flush=True)
    hits = sum(1 for row in results if row["hit"])
    print(json.dumps({"summary": f"{hits}/{len(results)} hit"}), flush=True)
    return results


def main() -> None:
    from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
    from starter.agent import Agent

    if "--harder" in sys.argv:
        run_harder_cases()
        return

    reuse = "--reuse-fixture" in sys.argv
    catalog = ROOT / "data" / "catalog.jsonl"
    dataset = ROOT / "data" / "public_set.jsonl"
    samples = load_jsonl(dataset)
    catalog_ids, categories, products = catalog_index(catalog)
    agent = Agent(catalog)

    recorder = RecordingAgent(agent)
    clean = evaluate(recorder, samples, catalog_ids, categories, products)
    if not reuse:
        write_fixture(samples, recorder.sessions)

    paraphrased = evaluate(ParaphraseAgent(agent), samples, catalog_ids, categories, products)

    print(json.dumps({"clean": metrics(clean), "paraphrased": metrics(paraphrased)}, indent=2))
    if not reuse:
        print(f"wrote {FIXTURE_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
