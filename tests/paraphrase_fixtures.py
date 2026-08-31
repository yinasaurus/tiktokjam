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


def main() -> None:
    from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
    from starter.agent import Agent

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
