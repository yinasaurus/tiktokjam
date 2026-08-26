"""Shared shopping lexicons. Used at index time and query time."""

from __future__ import annotations

import re

COLORS: frozenset[str] = frozenset(
    {
        "black",
        "white",
        "red",
        "blue",
        "green",
        "navy",
        "pink",
        "grey",
        "gray",
        "brown",
        "beige",
        "purple",
        "yellow",
        "orange",
        "gold",
        "silver",
        "khaki",
        "ivory",
        "maroon",
        "teal",
        "cream",
        "tan",
        "olive",
        "burgundy",
        "coral",
        "turquoise",
    }
)

MATERIALS: frozenset[str] = frozenset(
    {
        "cotton",
        "polyester",
        "nylon",
        "leather",
        "wool",
        "spandex",
        "silk",
        "rayon",
        "linen",
        "denim",
        "suede",
        "canvas",
        "fleece",
        "cashmere",
        "fabric",
    }
)

_SIZE_RE = re.compile(
    r"^(?:eu|us|uk)?-?\d{1,2}(?:[./]\d)?$|^(?:xxs|xs|s|m|l|xl|xxl|xxxl|2xl|3xl)$"
)

_ATTR_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "color",
        "colour",
        "color name",
        "size",
        "sizes",
        "material",
        "fabric",
        "brand",
        "style",
        "fit",
    }
)


def looks_like_size(token: str) -> bool:
    t = token.lower().replace(" ", "")
    return bool(_SIZE_RE.match(t))


def guess_attribute(phrase: str) -> str | None:
    tokens = phrase.lower().split()
    compact = phrase.lower().replace(" ", "")
    if any(t in COLORS for t in tokens) or compact in COLORS:
        return "color"
    if any(t in MATERIALS for t in tokens):
        return "material"
    if looks_like_size(compact) or any(looks_like_size(t) for t in tokens):
        return "size"
    return None


TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "shirt": ("shirt", "shirts", "t-shirt", "t-shirts", "tee"),
    "shirts": ("shirt", "shirts", "t-shirt", "t-shirts"),
    "tee": ("tee", "t-shirt", "t-shirts", "shirt"),
    "tshirt": ("t-shirt", "t-shirts", "shirt", "shirts"),
    "t-shirt": ("t-shirt", "t-shirts", "shirt"),
    "t-shirts": ("t-shirt", "t-shirts", "shirt", "shirts"),
    "shoe": ("shoe", "shoes"),
    "shoes": ("shoe", "shoes"),
    "boot": ("boot", "boots"),
    "boots": ("boot", "boots"),
    "jean": ("jean", "jeans"),
    "jeans": ("jean", "jeans"),
    "dress": ("dress", "dresses"),
    "hoodie": ("hoodie", "hoodies"),
    "short": ("short", "shorts"),
    "shorts": ("short", "shorts"),
    "clog": ("clog", "clogs"),
    "sandal": ("sandal", "sandals"),
}


def expand_terms(normalised: str) -> list[str]:
    """Query tokens plus shirt/shirts style aliases, first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    if not normalised:
        return out
    for tok in normalised.lower().split():
        variants = TYPE_ALIASES.get(tok, (tok,))
        for v in variants:
            if v not in seen:
                seen.add(v)
                out.append(v)
    if normalised not in seen:
        out.append(normalised)
    return out


def is_slot_token(normalised: str) -> bool:
    """True for a short value we should index even as a 1-gram."""
    if not normalised:
        return False
    if " " not in normalised and (normalised in COLORS or normalised in MATERIALS):
        return True
    return looks_like_size(normalised.replace(" ", ""))
