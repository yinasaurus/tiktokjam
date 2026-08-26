"""A1 — ask_attribute enum matches docs/agent_api_contract.json."""

from agent.config import ALLOWED_ASK_ATTRIBUTES

OFFICIAL = (
    "category",
    "material",
    "color",
    "size",
    "style",
    "brand",
    "budget",
    "feature",
    "use_case",
    "other",
)


def test_ask_attribute_enum_matches_kit():
    assert ALLOWED_ASK_ATTRIBUTES == OFFICIAL
