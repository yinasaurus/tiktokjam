from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


class PresetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_prompt: str | None = None
        self.presets: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "button":
            return
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        if "preset" in classes:
            self._current_prompt = attr_map.get("data-prompt") or ""

    def handle_data(self, data: str) -> None:
        if self._current_prompt is not None:
            label = data.strip()
            if label:
                self.presets.append((label, self._current_prompt))
                self._current_prompt = None


def test_demo_ui_has_expected_preset_prompts() -> None:
    html = Path("ui/static/index.html").read_text(encoding="utf-8")
    parser = PresetParser()
    parser.feed(html)

    presets = dict(parser.presets)
    assert presets == {
        "Buying": "navy cotton t-shirts",
        "Browsing": "I'm looking for Men Shorts, but I'm still exploring.",
        "Override 1": "I'm looking for Men Accessories. cotton.",
        "Override 2": "Actually, ignore my earlier preference. What I need is: leather.",
        "Boundary": "I don't have a preference for color; please use your judgment.",
    }
