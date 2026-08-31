# Hybrid research stack. The submitted evaluator path is
# `from starter.agent import Agent` -> agent.fast_agent.Agent.
# Import determinism FIRST so BLAS thread pins land before numpy (NFR-10).
from agent.determinism import pin_runtime

pin_runtime()

__all__ = ["Agent", "Config"]


def __getattr__(name: str):
    if name == "Agent":
        from agent.agent import Agent

        return Agent
    if name == "Config":
        from agent.config import Config

        return Config
    raise AttributeError(name)
