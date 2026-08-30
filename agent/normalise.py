"""THE shared phrase normaliser (TDD §3.3).

Index-time and query-time MUST import this function from this module.
A mismatch here is the most likely cause of a silently dead exact-phrase route.
"""

from __future__ import annotations

import html
import re
from functools import lru_cache

# Keep intra-word hyphens; drop other punctuation.
_PUNCT_RE = re.compile(r"[^\w\s-]", flags=re.UNICODE)
_MULTI_HYPHEN_RE = re.compile(r"-{2,}")
_WS_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Packaging / section-header boilerplate. Conservative on purpose —
# over-stripping "cotton" out of a real constraint is worse than leaving noise.
PACKAGING_STOPLIST: frozenset[str] = frozenset(
    {
        "description",
        "feature",
        "features",
        "package",
        "packaging",
        "including",
        "includes",
        "specification",
        "specifications",
        "spec",
        "specs",
    }
)

HEADER_STOPLIST: frozenset[str] = frozenset(
    {
        "description",
        "feature",
        "features",
        "package including",
        "package includes",
        "specifications",
        "specification",
    }
)


def strip_html(text: str) -> str:
    if "<" in text:
        text = _HTML_TAG_RE.sub(" ", text)
    if "&" in text:
        text = html.unescape(text)
    return text


@lru_cache(maxsize=200_000)
def normalise(phrase: str) -> str:
    """Lowercase, unescape, strip punctuation except intra-word hyphen, collapse ws.

    Tokens that are packaging boilerplate are dropped. Empty input → "".
    """
    if phrase is None:
        return ""
    s = strip_html(str(phrase)).lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _MULTI_HYPHEN_RE.sub("-", s)
    s = _WS_RE.sub(" ", s).strip()
    if not s:
        return ""
    kept: list[str] = []
    for tok in s.split(" "):
        tok = tok.strip("-_")
        if not tok:
            continue
        if tok in PACKAGING_STOPLIST:
            continue
        kept.append(tok)
    return " ".join(kept)


def token_count(normalised: str) -> int:
    if not normalised:
        return 0
    return len(normalised.split(" "))


def is_indexable_phrase(normalised: str, min_tokens: int = 2, max_tokens: int = 8) -> bool:
    n = token_count(normalised)
    return min_tokens <= n <= max_tokens


def ngrams(normalised: str, n_min: int, n_max: int) -> list[str]:
    """Slide an n-gram window over an already-normalised string."""
    if not normalised:
        return []
    tokens = normalised.split(" ")
    out: list[str] = []
    upper = min(n_max, len(tokens))
    for n in range(n_min, upper + 1):
        limit = len(tokens) - n + 1
        for i in range(limit):
            out.append(" ".join(tokens[i : i + n]))
    return out
