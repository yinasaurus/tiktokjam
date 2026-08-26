"""Official Agent entry. The local evaluator does `from starter.agent import Agent`.

Do not put retrieval logic here. Implementation lives in the `agent` package so
this file stays a thin adapter for `docs/agent_api_contract.json`.
The BM25 starter shipped in the kit is preserved as `starter/bm25_baseline.py`.
"""

from agent.agent import Agent

__all__ = ["Agent"]
