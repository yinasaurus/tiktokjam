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
        "charcoal",
        "charcoalgrey",
        "mint",
        "lavender",
        "lilac",
        "mustard",
        "rust",
        "wine",
        "rose",
        "peach",
        "nude",
        "camel",
        "chocolate",
        "magenta",
        "fuchsia",
        "violet",
        "indigo",
        "aqua",
        "blush",
        "mauve",
        "plum",
        "sage",
        "forest",
        "hunter",
        "camo",
        "camouflage",
        "bronze",
        "copper",
        "champagne",
        "royal",
        "sky",
        "heather",
        "oatmeal",
        "stone",
        "sand",
        "espresso",
        "offwhite",
        "creamwhite",
        "hotpink",
        "lightblue",
        "darkblue",
        "navyblue",
        "forestgreen",
        "neon",
        "multicolor",
        "multicolour",
        "rainbow",
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
        "viscose",
        "modal",
        "acrylic",
        "elastane",
        "lycra",
        "chiffon",
        "satin",
        "velvet",
        "corduroy",
        "tweed",
        "knit",
        "knitted",
        "mesh",
        "lace",
        "rubber",
        "synthetic",
        "bamboo",
        "hemp",
        "down",
        "microfiber",
        "microfibre",
        "jersey",
        "flannel",
        "twill",
        "poplin",
        "organza",
        "sequin",
        "sequins",
        "faux",
        "fauxleather",
        "vegan",
        "neoprene",
        "goretex",
        "cottonblend",
        "polyblend",
    }
)

SIZE_WORDS: frozenset[str] = frozenset(
    {
        "small",
        "medium",
        "large",
        "plus",
        "plussize",
        "onesize",
        "osfa",
        "petite",
        "tall",
        "wide",
        "narrow",
    }
)

STYLE_WORDS: frozenset[str] = frozenset(
    {
        "casual",
        "formal",
        "vintage",
        "athletic",
        "sporty",
        "business",
        "elegant",
        "boho",
        "streetwear",
        "classic",
        "modern",
        "minimalist",
        "preppy",
        "retro",
        "cute",
        "sexy",
        "edgy",
        "lounge",
        "smart",
    }
)

FIT_WORDS: frozenset[str] = frozenset(
    {
        "slim",
        "skinny",
        "relaxed",
        "regular",
        "oversized",
        "loose",
        "fitted",
        "cropped",
        "straight",
        "bootcut",
        "tapered",
        "wideleg",
        "boyfriend",
        "mom",
        "athletic",
    }
)

FEATURE_WORDS: frozenset[str] = frozenset(
    {
        "floral",
        "striped",
        "stripe",
        "plaid",
        "checked",
        "graphic",
        "logo",
        "solid",
        "printed",
        "print",
        "sequin",
        "lace",
        "mesh",
        "ripped",
        "distressed",
        "waterproof",
        "insulated",
        "breathable",
        "stretch",
        "lined",
    }
)

USE_CASE_WORDS: frozenset[str] = frozenset(
    {
        "gym",
        "workout",
        "training",
        "hiking",
        "yoga",
        "swimming",
        "beach",
        "wedding",
        "office",
        "work",
        "sleep",
        "party",
        "travel",
        "school",
        "running",
        "walking",
        "cycling",
        "tennis",
        "golf",
        "ski",
        "snow",
        "rain",
        "everyday",
        "weekend",
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
        "department",
        "gender",
        "occasion",
    }
)

MEN_WORDS: frozenset[str] = frozenset(
    {
        "male",
        "man",
        "men",
        "mens",
        "masculine",
        "him",
        "his",
        "boyfriend",
        "husband",
        "guy",
        "guys",
        "dude",
        "gentlemen",
        "gents",
        "menswear",
        "gentleman",
    }
)
WOMEN_WORDS: frozenset[str] = frozenset(
    {
        "female",
        "woman",
        "women",
        "womens",
        "ladies",
        "lady",
        "feminine",
        "her",
        "hers",
        "girlfriend",
        "wife",
        "gal",
        "gals",
        "womenswear",
        "misses",
    }
)

_MEN_INDEX = ("men", "man", "mens", "male")
_WOMEN_INDEX = ("women", "woman", "womens", "female")

GENDER_INDEX_TERMS: dict[str, tuple[str, ...]] = {
    "men": _MEN_INDEX,
    "women": _WOMEN_INDEX,
}

GENDER_ALIASES: dict[str, tuple[str, ...]] = {
    **{w: _MEN_INDEX for w in MEN_WORDS},
    **{w: _WOMEN_INDEX for w in WOMEN_WORDS},
}

GENDER_PHRASES: tuple[tuple[str, str], ...] = (
    ("for him", "men"),
    ("for her", "women"),
    ("for men", "men"),
    ("for women", "women"),
    ("for guys", "men"),
    ("for ladies", "women"),
    ("mens wear", "men"),
    ("womens wear", "women"),
)


def _alias_groups(*groups: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for group in groups:
        for key in group:
            out[key] = group
    return out


TYPE_ALIASES: dict[str, tuple[str, ...]] = _alias_groups(
    (
        "shirt",
        "shirts",
        "t-shirt",
        "t-shirts",
        "tee",
        "tees",
        "tshirt",
    ),
    ("polo", "polos"),
    ("blouse", "blouses", "blouses button-down shirts", "tunic", "tunics"),
    ("button-down", "buttondown", "oxford", "casual button-down shirts"),
    (
        "hoodie",
        "hoodies",
        "sweatshirt",
        "sweatshirts",
        "fashion hoodies sweatshirts",
        "pullover",
        "pullovers",
    ),
    ("tank", "tanks", "cami", "camis", "tanks camis"),
    ("jean", "jeans"),
    ("pant", "pants", "trousers", "slacks", "chinos"),
    ("short", "shorts", "active shorts"),
    ("skirt", "skirts"),
    ("dress", "dresses"),
    ("legging", "leggings"),
    ("jumpsuit", "jumpsuits", "romper", "rompers", "one-piece", "one-pieces"),
    ("sweater", "sweaters", "jumper", "jumpers", "cardigan", "cardigans"),
    ("jacket", "jackets", "coat", "coats"),
    ("shoe", "shoes"),
    ("sneaker", "sneakers", "trainer", "trainers", "fashion sneakers"),
    ("running", "road running"),
    ("flat", "flats"),
    ("pump", "pumps", "heel", "heels"),
    ("boot", "boots", "bootie", "booties", "ankle bootie"),
    ("sandal", "sandals", "heeled sandals"),
    ("slipper", "slippers"),
    ("loafer", "loafers", "loafers slip-ons"),
    ("clog", "clogs", "mule", "mules", "mules clogs"),
    ("oxfords",),
    ("wedge", "wedges", "platforms wedges"),
    ("flip-flop", "flip-flops", "flipflop", "flipflops"),
    ("slide", "slides"),
    ("watch", "watches", "wrist watches"),
    ("sunglass", "sunglasses", "shades"),
    ("hat", "hats", "cap", "caps"),
    ("beanie", "beanies", "skullies beanies"),
    ("sock", "socks", "athletic socks"),
    ("belt", "belts"),
    ("wallet", "wallets"),
    ("bag", "bags", "purse", "handbag", "handbags"),
    ("tote", "totes"),
    ("backpack", "backpacks"),
    ("crossbody", "crossbody bags"),
    ("necklace", "necklaces"),
    ("pendant", "pendants", "pendant necklaces"),
    ("ring", "rings"),
    ("bra", "bras"),
    ("costume", "costumes"),
    ("pajama", "pajamas", "pyjama", "pyjamas", "robe", "robes", "nightgown"),
)

PHRASE_ALIASES: dict[str, tuple[str, ...]] = {
    "t shirt": ("t-shirt", "t-shirts", "tee", "tees"),
    "t shirts": ("t-shirt", "t-shirts", "tee", "tees"),
    "tee shirt": ("t-shirt", "t-shirts", "tee"),
    "button down": ("casual button-down shirts", "button-down"),
    "button down shirt": ("casual button-down shirts",),
    "running shoes": ("road running", "running", "sneakers", "fashion sneakers"),
    "running shoe": ("road running", "running", "sneakers"),
    "gym shoes": ("fashion sneakers", "sneakers", "training"),
    "wrist watch": ("wrist watches", "watches"),
    "wrist watches": ("wrist watches", "watches"),
    "for him": _MEN_INDEX,
    "for her": _WOMEN_INDEX,
    "for men": _MEN_INDEX,
    "for women": _WOMEN_INDEX,
    "sweat shirt": ("sweatshirt", "sweatshirts", "hoodie", "hoodies"),
    "hood ie": ("hoodie", "hoodies"),
    "flip flops": ("flip-flops", "sandals"),
    "high heels": ("pumps", "heels", "heeled sandals"),
    "sports bra": ("sports bras", "bras"),
    "everyday bra": ("everyday bras", "bras"),
    "baseball cap": ("baseball caps", "caps", "hats"),
    "cross body": ("crossbody", "crossbody bags"),
    "sleep shirt": ("nightgowns sleepshirts", "pajamas"),
}


def looks_like_size(token: str) -> bool:
    t = token.lower().replace(" ", "")
    return bool(_SIZE_RE.match(t))


def canonical_gender(text: str) -> str | None:
    """Map male/men/mens and female/women/womens to men|women. Mixed → None."""
    if not text:
        return None
    compact = text.lower().replace("'", "").replace("-", "")
    padded = f" {compact} "
    found: set[str] = set()
    for phrase, gender in GENDER_PHRASES:
        if f" {phrase} " in padded:
            found.add(gender)
    tokens = compact.split()
    for src in (*tokens, compact.replace(" ", "")):
        if src in MEN_WORDS:
            found.add("men")
        elif src in WOMEN_WORDS:
            found.add("women")
    if found == {"men"}:
        return "men"
    if found == {"women"}:
        return "women"
    return None


def infer_department(
    category_path: tuple[str, ...] | list[str],
    details: dict[str, str] | None,
    title: str,
) -> str:
    """Prefer category path (Men/Women), then details, then title."""
    path_text = " ".join(str(c) for c in category_path)
    gender = canonical_gender(path_text)
    if gender:
        return gender
    if details:
        for key in ("department", "gender"):
            val = details.get(key)
            if val:
                gender = canonical_gender(str(val))
                if gender:
                    return gender
    return canonical_gender(title) or ""


def guess_attribute(phrase: str) -> str | None:
    tokens = phrase.lower().split()
    compact = phrase.lower().replace(" ", "").replace("-", "")
    if canonical_gender(phrase):
        return "department"
    if any(t in COLORS for t in tokens) or compact in COLORS:
        return "color"
    if any(t in MATERIALS for t in tokens) or compact in MATERIALS:
        return "material"
    if (
        compact in SIZE_WORDS
        or looks_like_size(compact)
        or any(looks_like_size(t) or t in SIZE_WORDS for t in tokens)
    ):
        return "size"
    if any(t in FEATURE_WORDS for t in tokens) or compact in FEATURE_WORDS:
        return "feature"
    if any(t in USE_CASE_WORDS for t in tokens) or compact in USE_CASE_WORDS:
        return "use_case"
    if any(t in FIT_WORDS or t in STYLE_WORDS for t in tokens) or compact in FIT_WORDS or compact in STYLE_WORDS:
        return "style"
    return None


def expand_terms(normalised: str) -> list[str]:
    """Query tokens plus type/gender aliases, first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    if not normalised:
        return out

    def add(term: str) -> None:
        if term and term not in seen:
            seen.add(term)
            out.append(term)

    n = normalised.lower()
    for tok in n.split():
        variants = TYPE_ALIASES.get(tok) or GENDER_ALIASES.get(tok) or (tok,)
        for v in variants:
            add(v)
    padded = f" {n} "
    for phrase, variants in PHRASE_ALIASES.items():
        if f" {phrase} " in padded:
            for v in variants:
                add(v)
    add(n)
    return out


def is_slot_token(normalised: str) -> bool:
    """True for a short value we should index even as a 1-gram."""
    if not normalised:
        return False
    if " " not in normalised and (
        normalised in COLORS
        or normalised in MATERIALS
        or normalised in MEN_WORDS
        or normalised in WOMEN_WORDS
        or normalised in SIZE_WORDS
        or normalised in STYLE_WORDS
        or normalised in FIT_WORDS
        or normalised in USE_CASE_WORDS
        or normalised in FEATURE_WORDS
    ):
        return True
    return looks_like_size(normalised.replace(" ", ""))
