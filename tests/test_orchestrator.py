"""Tests for the Orchestrator."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agents.llm import MockLLM
from models import AgentRole
from orchestrator import Orchestrator


@pytest.fixture
def orchestrator() -> Orchestrator:
    return Orchestrator(llm=MockLLM())


class TestOrchestrator:
    def test_run_returns_workflow_state(self, orchestrator: Orchestrator) -> None:
        state = orchestrator.run("Build a memory management application")
        assert state is not None

    def test_all_agents_ran(self, orchestrator: Orchestrator) -> None:
        state = orchestrator.run("Build a memory management application")
        assert state.requirement_spec is not None
        assert state.architecture_spec is not None
        assert state.build_result is not None
        assert state.test_result is not None

    def test_history_contains_messages_from_all_agents(
        self, orchestrator: Orchestrator
    ) -> None:
        state = orchestrator.run("Build a memory management application")
        senders = {m.sender for m in state.history}
        # At minimum the first pass through all four agents.
        assert AgentRole.BUSINESS_ANALYST in senders
        assert AgentRole.ARCHITECT in senders
        assert AgentRole.BUILDER in senders
        assert AgentRole.TESTER in senders

    def test_iteration_count_bounded(self, orchestrator: Orchestrator) -> None:
        """The orchestrator must not iterate more than MAX_ITERATIONS times."""
        import config

        state = orchestrator.run("Build a memory management application")
        assert state.iteration_count <= config.MAX_ITERATIONS

    def test_original_requirement_preserved(
        self, orchestrator: Orchestrator
    ) -> None:
        req = "Build a note-taking service"
        state = orchestrator.run(req)
        assert state.original_requirement == req

    def test_custom_llm_injected(self) -> None:
        mock = MockLLM()
        orc = Orchestrator(llm=mock)
        # Verify every agent uses the injected LLM (duck-type check).
        for agent in orc._agents.values():
            assert agent._llm is mock

    def test_progress_callback_receives_agent_updates(self) -> None:
        events: list[AgentRole] = []
        orc = Orchestrator(llm=MockLLM())
        orc.run(
            "Build a memory management application",
            progress_callback=lambda role, _state: events.append(role),
        )
        assert AgentRole.BUSINESS_ANALYST in events
        assert AgentRole.ARCHITECT in events
        assert AgentRole.BUILDER in events
        assert AgentRole.TESTER in events
