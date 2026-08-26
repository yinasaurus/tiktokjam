"""Official entrypoint is starter.agent.Agent (evaluator import path)."""

from agent.agent import Agent as ImplAgent
from starter.agent import Agent as StarterAgent


def test_starter_reexports_implementation():
    assert StarterAgent is ImplAgent
