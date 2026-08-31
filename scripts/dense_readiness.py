"""Print whether the optional dense/Model2Vec path is actually usable.

This script is research-only. It does not change the default submission agent.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import Config
from agent.routes.dense import load_encoder


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _encoder_files(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(
        str(p.relative_to(path)).replace("\\", "/")
        for p in path.rglob("*")
        if p.is_file() and p.name.lower() != "readme.md"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check dense/Model2Vec readiness")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument(
        "--init-agent",
        action="store_true",
        help="Also instantiate agent.agent.Agent against the catalog and report dense availability.",
    )
    args = parser.parse_args()

    config = Config()
    encoder_dir = Path(config.encoder_dir)
    files = _encoder_files(encoder_dir)
    info: dict[str, object] = {
        "model2vec_installed": _module_available("model2vec"),
        "numpy_installed": _module_available("numpy"),
        "bm25s_installed": _module_available("bm25s"),
        "encoder_dir": str(encoder_dir),
        "encoder_artifact_files": files,
        "encoder_artifact_file_count": len(files),
        "encoder_loads": False,
        "encoder_type": None,
        "encoder_dim": None,
        "agent_checked": False,
    }

    encoder = load_encoder(config)
    if encoder is not None:
        info["encoder_loads"] = True
        info["encoder_type"] = type(encoder).__name__
        info["encoder_dim"] = getattr(encoder, "dim", None)

    if args.init_agent:
        from agent.agent import Agent

        t0 = time.perf_counter()
        agent = Agent(args.catalog)
        info["agent_checked"] = True
        info["agent_init_seconds"] = round(time.perf_counter() - t0, 3)
        info["agent_catalog_size"] = len(agent.catalog)
        info["agent_dense_available"] = bool(agent.dense.available)
        info["agent_encoder_type"] = type(agent.encoder).__name__ if agent.encoder else None
        info["agent_lexical_available"] = bool(agent.lexical.available)

    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
