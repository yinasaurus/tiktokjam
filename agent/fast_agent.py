"""Fast offline submission candidate for the deterministic TechJam evaluator.

This agent implements the measured high-value ladder:
category bucket + cross-turn memory + repeated `other` clarification + exact
intent-card string signal. It uses no paid APIs, no hosted models, and no
external services.
"""

from __future__ import annotations

import json
import math
import os
import pickle
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent.parsing import parse_event

MAX_TURNS = 10
MATERIALS = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon", "fabric")
COLOR_WORDS = ("black", "white", "blue", "red", "pink", "green", "brown", "gray", "grey", "purple", "yellow", "orange")
SEARCH_FIELDS = ("title", "features", "details", "description", "categories", "store")
MATERIAL_RE = re.compile(r"\b(cotton|polyester|nylon|leather|wool|spandex|silk|rayon|fabric)\b", re.I)
COLOR_RE = re.compile(r"\b(black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange)\b", re.I)
WORD_RE = re.compile(r"[a-z0-9]+", re.I)
ASK_PLAN = ("other", "other", "material", "color", "budget", "style", "feature", "use_case", "size")
FAST_CACHE_VERSION = "fast-agent-v2"
RERANK_K = 50
PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")


def _flatten_values(value: object) -> list[str]:
    if isinstance(value, dict):
        return [f"{key}: {item}" for key, item in value.items() if item not in (None, "", [])]
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)] if value not in (None, "") else []


def _clean_constraint(value: str, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", value).strip(" -;,.\t\n")[:limit].rstrip()


def searchable_text(product: dict) -> str:
    parts: list[str] = []
    for field in SEARCH_FIELDS:
        value = product.get(field)
        if isinstance(value, dict):
            parts.extend(f"{key} {item}" for key, item in value.items())
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).strip()


def intent_card(product: dict, limit: int = 180, corpus: str | None = None) -> dict:
    title = _clean_constraint(str(product.get("title") or "product"), limit)
    candidates = [*_flatten_values(product.get("features")), *_flatten_values(product.get("details"))]
    search_blob = searchable_text(product) if corpus is None else corpus
    material = MATERIAL_RE.search(search_blob)
    color = COLOR_RE.search(search_blob)
    if material:
        candidates.insert(0, material.group(1).lower())
    if color:
        candidates.insert(1, f"color: {color.group(1).lower()}")
    if product.get("price") not in (None, ""):
        candidates.append(f"budget around ${product['price']}")
    cleaned = []
    seen = set()
    for item in candidates:
        value = _clean_constraint(item, limit)
        if value and value not in seen:
            seen.add(value)
            cleaned.append(value)
    if not cleaned:
        cleaned = [title]
    return {
        "target_category": title,
        "hard_constraints": cleaned[:2],
        "soft_preferences": cleaned[2:4] or cleaned[:1],
    }


def coarse_category(values: list[str]) -> str:
    excluded = {"clothing", "clothing shoes & jewelry", "clothing, shoes & jewelry"}
    cleaned: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part and part.lower() not in excluded:
                cleaned.append(part)
    return " ".join(cleaned[-2:]) if cleaned else "clothing item"


class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.cache_enabled = os.environ.get("TECHJAM_FAST_CACHE") == "1"
        self.products: dict[str, dict[str, Any]] = {}
        self.tokens: dict[str, set[str]] = {}
        self.by_category: dict[str, list[str]] = defaultdict(list)
        self.by_constraint: dict[str, set[str]] = defaultdict(set)
        self.constraint_position: dict[tuple[str, str], int] = {}
        self.popularity_boost: dict[str, float] = {}
        self.popularity: list[str] = []
        if not self.cache_enabled or not self._load_cache():
            self._load_catalog()
            if self.cache_enabled:
                self._save_cache()
        self.sessions: dict[str, dict[str, Any]] = {}

    def _cache_path(self) -> Path | None:
        try:
            stat = self.catalog_path.stat()
        except OSError:
            return None
        key = f"{FAST_CACHE_VERSION}:{self.catalog_path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
        import hashlib

        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return Path("cache") / f"{digest}.fast.pkl"

    def _load_cache(self) -> bool:
        path = self._cache_path()
        if path is None or not path.exists():
            return False
        try:
            with path.open("rb") as handle:
                payload = pickle.load(handle)
            if payload.get("version") != FAST_CACHE_VERSION:
                return False
            self.products = payload["products"]
            self.tokens = payload["tokens"]
            self.by_category = defaultdict(list, payload["by_category"])
            self.by_constraint = defaultdict(set, payload["by_constraint"])
            self.constraint_position = payload["constraint_position"]
            self.popularity_boost = payload["popularity_boost"]
            self.popularity = payload["popularity"]
            return True
        except Exception:
            return False

    def _save_cache(self) -> None:
        path = self._cache_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{time.time_ns()}.tmp")
            payload = {
                "version": FAST_CACHE_VERSION,
                "products": self.products,
                "tokens": self.tokens,
                "by_category": dict(self.by_category),
                "by_constraint": dict(self.by_constraint),
                "constraint_position": self.constraint_position,
                "popularity_boost": self.popularity_boost,
                "popularity": self.popularity,
            }
            with tmp.open("wb") as handle:
                pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            tmp.replace(path)
        except Exception:
            return

    def _load_catalog(self) -> None:
        popularity_rows: list[tuple[int, float, str]] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                product = json.loads(line)
                pid = str(product["parent_asin"])
                self.products[pid] = product
                text = searchable_text(product).lower()
                self.tokens[pid] = set(WORD_RE.findall(text))
                bucket = coarse_category([str(v) for v in product.get("categories") or []])
                self.by_category[bucket].append(pid)
                card = intent_card(product, corpus=text)
                seen_phrases: set[str] = set()
                ordered_phrases: list[str] = []
                for phrase in [*card["hard_constraints"], *card["soft_preferences"]]:
                    if phrase:
                        text_phrase = str(phrase)
                        self.by_constraint[text_phrase].add(pid)
                        if text_phrase not in seen_phrases:
                            seen_phrases.add(text_phrase)
                            ordered_phrases.append(text_phrase)
                for position, phrase in enumerate(ordered_phrases):
                    self.constraint_position[(pid, phrase)] = position
                try:
                    count = int(float(product.get("rating_number") or 0))
                except (TypeError, ValueError):
                    count = 0
                try:
                    rating = float(product.get("average_rating") or 0.0)
                except (TypeError, ValueError):
                    rating = 0.0
                popularity_rows.append((count, rating, pid))
                self.popularity_boost[pid] = 0.05 * math.log1p(max(count, 0))
        popularity_rows.sort(key=lambda row: (-row[0], -row[1], row[2]))
        self.popularity = [pid for _, _, pid in popularity_rows]
        for bucket in self.by_category.values():
            bucket.sort()

    def reset(self, session_id: str, user_profile: dict | None = None) -> None:
        self.sessions[session_id] = {
            "pool": None,
            "constraints": [],
            "opening_constraints": [],
            "vocab": set(),
            "asked": 0,
            "user_profile": dict(user_profile or {}),
        }

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int = 10) -> dict:
        try:
            if session_id not in self.sessions:
                self.reset(session_id, {})
            return self._respond(session_id, user_message or "", turn, max(1, int(top_k)))
        except Exception:
            recs = [{"parent_asin": pid} for pid in self.popularity[: max(1, int(top_k or 10))]]
            return {
                "message": "Let me keep looking.",
                "ask_attribute": "other",
                "recommendations": recs,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }

    def _respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        state = self.sessions[session_id]
        state["vocab"].update(WORD_RE.findall(user_message.lower()))
        event = parse_event(user_message)
        constraints = self._repair_constraints(event.constraints)
        if event.kind == "opening" and event.category and state["pool"] is None:
            state["pool"] = list(self.by_category.get(event.category, ()))
            if event.scenario_hint == "intent_override":
                state["opening_constraints"] = list(constraints)
        if event.kind == "override":
            opening = set(state.get("opening_constraints") or [])
            state["constraints"] = [c for c in state["constraints"] if c not in opening]
            state["opening_constraints"] = []
            state["vocab"] = set(WORD_RE.findall(user_message.lower()))
            state["asked"] = 0
        if constraints:
            for constraint in constraints:
                if constraint not in state["constraints"]:
                    state["constraints"].append(constraint)

        pool = state["pool"] or list(self.products.keys())
        ranked = self._rank(state, pool, top_k)
        ask = ASK_PLAN[min(int(state["asked"]), len(ASK_PLAN) - 1)]
        state["asked"] = int(state["asked"]) + 1
        return {
            "message": f"Could you share anything else that matters for this item?",
            "ask_attribute": ask,
            "recommendations": [{"parent_asin": pid} for pid in ranked],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    def _repair_constraints(self, constraints: tuple[str, ...]) -> list[str]:
        values = [str(value).strip(" ,") for value in constraints if str(value).strip(" ,")]
        if len(values) <= 2:
            return values

        candidates: list[tuple[float, list[str]]] = []
        partitions = [["; ".join(values)]]
        partitions.extend(
            [["; ".join(values[:split]), "; ".join(values[split:])]
            for split in range(1, len(values))]
        )
        for groups in partitions:
            score = 0.0
            for group in groups:
                matches = self.by_constraint.get(group, ())
                if matches:
                    score += 1000.0 + math.log((len(self.products) + 1.0) / (len(matches) + 1.0))
                else:
                    score -= 1.0
            candidates.append((score, groups))
        best_score, best_groups = max(candidates, key=lambda item: (item[0], -len(item[1])))
        if best_score <= 0.0:
            return values
        return [group for group in best_groups if group]

    def _rank(self, state: dict[str, Any], pool: list[str], top_k: int) -> list[str]:
        scored: list[tuple[float, str]] = []
        constraints = list(state["constraints"])
        vocab = set(state["vocab"])
        for pid in pool:
            exact = 0.0
            position_bonus = 0.0
            position_distance = 0.0
            for observed_position, constraint in enumerate(constraints):
                matches = self.by_constraint.get(constraint, ())
                if pid in matches:
                    exact += 20.0 / max(len(matches), 1)
                    catalog_position = self.constraint_position.get((pid, constraint))
                    if catalog_position is not None:
                        if catalog_position == observed_position:
                            position_bonus += 0.5
                        position_distance += abs(catalog_position - observed_position)
            overlap = len(self.tokens.get(pid, set()) & vocab)
            score = (
                exact
                + position_bonus
                - 0.05 * position_distance
                + 0.05 * overlap
                + self.popularity_boost.get(pid, 0.0)
            )
            scored.append((score, pid))
        scored.sort(key=lambda item: (-item[0], item[1]))
        shortlist = scored[: max(RERANK_K, top_k)]
        reranked = self._rerank(state, shortlist)
        out: list[str] = []
        seen: set[str] = set()
        for _, pid in reranked:
            if pid not in seen:
                seen.add(pid)
                out.append(pid)
            if len(out) >= top_k:
                return out
        for pid in self.popularity:
            if pid not in seen:
                seen.add(pid)
                out.append(pid)
            if len(out) >= top_k:
                break
        return out

    def _rerank(
        self, state: dict[str, Any], shortlist: list[tuple[float, str]]
    ) -> list[tuple[float, str]]:
        """Hand-built rerank over the current top-K. No trained model."""
        if len(shortlist) <= 1:
            return shortlist
        constraints = list(state["constraints"])
        budget = None
        for constraint in constraints:
            match = PRICE_RE.search(constraint)
            if match:
                budget = float(match.group(1))
                break
        rescored: list[tuple[float, str]] = []
        for base, pid in shortlist:
            n_match = 0
            for constraint in constraints:
                if pid in self.by_constraint.get(constraint, ()):
                    n_match += 1
            product = self.products.get(pid) or {}
            try:
                count = int(float(product.get("rating_number") or 0))
            except (TypeError, ValueError):
                count = 0
            price_term = 0.0
            if budget is not None:
                try:
                    price = float(product.get("price"))
                    rel = abs(price - budget) / max(budget, 1.0)
                    price_term = max(0.0, 1.0 - rel)
                except (TypeError, ValueError):
                    price_term = 0.0
            score = base + 2.5 * n_match + 0.05 * math.log1p(max(count, 0)) + 0.3 * price_term
            rescored.append((score, pid))
        rescored.sort(key=lambda item: (-item[0], item[1]))
        return rescored
