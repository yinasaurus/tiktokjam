"""Local demo UI. Not part of scoring — the harness stays headless."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.types import asins_of

STATIC_DIR = Path(__file__).resolve().parent / "static"
OFFICIAL_CATALOG = ROOT / "data" / "catalog.jsonl"
FIXTURE_CATALOG = ROOT / "tests" / "fixtures" / "catalog.jsonl"

_lock = threading.Lock()
_agent = None
_error: str | None = None
_ready = False
_catalog_size = 0
_selected_catalog = OFFICIAL_CATALOG
_turns: dict[str, int] = {}


def _catalog_path() -> Path:
    if _selected_catalog == FIXTURE_CATALOG:
        return FIXTURE_CATALOG
    if _selected_catalog.exists():
        return _selected_catalog
    return FIXTURE_CATALOG


def _load_agent() -> None:
    global _agent, _error, _ready, _catalog_size
    from starter.agent import Agent

    path = _catalog_path()
    try:
        agent = Agent(path)
        with _lock:
            _agent = agent
            catalog = getattr(agent, "products", None) or getattr(agent, "catalog", [])
            _catalog_size = len(catalog)
            _ready = True
    except Exception as exc:
        with _lock:
            _error = f"{type(exc).__name__}: {exc}"
            _ready = False


def _product_card(agent, asin: str) -> dict:
    product = None
    if hasattr(agent, "products"):
        product = agent.products.get(asin)
    elif hasattr(agent, "catalog"):
        product = agent.catalog.get(asin)
    if product is None:
        return {"parent_asin": asin, "title": asin}
    if isinstance(product, dict):
        price = product.get("price")
        try:
            price = None if price is None else round(float(price), 2)
        except (TypeError, ValueError):
            price = None
        try:
            rating = product.get("average_rating")
            rating = None if rating is None else round(float(rating), 2)
        except (TypeError, ValueError):
            rating = None
        categories = [str(item) for item in product.get("categories") or []]
        details = product.get("details") if isinstance(product.get("details"), dict) else {}
        return {
            "parent_asin": asin,
            "title": product.get("title") or asin,
            "price": price,
            "category": categories[-1] if categories else None,
            "categories": categories,
            "store": product.get("store") or None,
            "department": details.get("Department"),
            "rating": rating,
            "rating_count": product.get("rating_number") or 0,
            "features": list(product.get("features") or []),
            "description": " ".join(str(item) for item in product.get("description") or []),
            "details": dict(details),
            "sparse": False,
        }
    price = None if product.price is None else round(product.price, 2)
    rating = None if not product.avg_rating else round(product.avg_rating, 2)
    return {
        "parent_asin": asin,
        "title": product.title or asin,
        "price": price,
        "category": product.leaf_category,
        "categories": list(product.category_path),
        "store": product.store or None,
        "department": product.department or None,
        "rating": rating,
        "rating_count": product.rating_count,
        "features": list(product.features),
        "description": product.description or "",
        "details": dict(product.details),
        "sparse": product.is_sparse,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            html = (STATIC_DIR / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/api/health":
            with _lock:
                self._json(
                    200,
                    {
                        "ready": _ready,
                        "error": _error,
                        "catalog_size": _catalog_size,
                        "catalog_mode": "fixture" if _selected_catalog == FIXTURE_CATALOG else "official",
                        "catalog_label": (
                            "Demo fixture catalog"
                            if _selected_catalog == FIXTURE_CATALOG
                            else "Official 50k catalog"
                        ),
                    },
                )
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        path = urlparse(self.path).path
        if path == "/api/reset":
            self._reset(body)
            return
        if path == "/api/turn":
            self._turn(body)
            return
        self._json(404, {"error": "not found"})

    def _reset(self, body: dict) -> None:
        if not _ready or _agent is None:
            self._json(503, {"error": _error or "agent still loading"})
            return
        session_id = str(body.get("session_id") or "ui")
        with _lock:
            _agent.reset(session_id, {})
            _turns[session_id] = 1
        self._json(200, {"ok": True, "turn": 1})

    def _turn(self, body: dict) -> None:
        if not _ready or _agent is None:
            self._json(503, {"error": _error or "agent still loading"})
            return
        session_id = str(body.get("session_id") or "ui")
        message = str(body.get("message") or "").strip()
        if not message:
            self._json(400, {"error": "empty message"})
            return
        with _lock:
            turn = _turns.get(session_id, 1)
            sessions = getattr(_agent, "sessions", getattr(_agent, "_sessions", {}))
            if session_id not in sessions:
                _agent.reset(session_id, {})
                turn = 1
            out = _agent.respond(session_id, message, turn=turn, top_k=10)
            asins = asins_of(out)
            cards = [_product_card(_agent, asin) for asin in asins]
            _turns[session_id] = min(turn + 1, 10)
            next_turn = _turns[session_id]
        self._json(
            200,
            {
                "message": out.get("message") or "",
                "ask_attribute": out.get("ask_attribute"),
                "recommendations": cards,
                "turn": turn,
                "next_turn": next_turn,
            },
        )


def main() -> None:
    global _selected_catalog
    parser = argparse.ArgumentParser(description="Demo UI for the shopping agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use the tiny test catalog for instant UI demos. Not for scoring.",
    )
    args = parser.parse_args()
    if args.fixture:
        _selected_catalog = FIXTURE_CATALOG
    threading.Thread(target=_load_agent, daemon=True).start()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Demo UI (not scored): {url}")
    print(f"Indexing {_catalog_path()} in the background...")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
