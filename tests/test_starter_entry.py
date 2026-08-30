"""Official entrypoint is starter.agent.Agent (evaluator import path)."""

from agent.fast_agent import Agent as FastAgent
from starter.agent import Agent as StarterAgent
from starter.agent import HybridAgent


def test_starter_exports_submission_agent():
    assert StarterAgent is FastAgent


def test_starter_keeps_hybrid_agent_available():
    assert HybridAgent.__name__ == "Agent"
