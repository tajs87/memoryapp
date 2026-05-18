"""Tests for the Tester Agent."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agents.llm import MockLLM
from agents.tester import TesterAgent
from models import (
    AgentRole,
    ArchitectureSpec,
    BuildResult,
    MessageType,
    RequirementSpec,
    WorkflowState,
)


@pytest.fixture
def agent() -> TesterAgent:
    return TesterAgent(llm=MockLLM())


@pytest.fixture
def state_with_build() -> WorkflowState:
    state = WorkflowState(original_requirement="Build a memory app")
    state.requirement_spec = RequirementSpec(
        original_requirement="Build a memory app",
        clarified_requirements=["Users can create notes"],
    )
    state.architecture_spec = ArchitectureSpec(
        architectural_requirements=["Authenticated CRUD APIs"],
        system_overview="Three-tier web app",
    )
    state.build_result = BuildResult(
        success=True,
        implementation_summary="Implemented authenticated CRUD APIs.",
        completed_requirements=["Users can create notes"],
        unit_tests=["test_create_memory"],
        regression_tests=["test_unicode_search"],
        collaboration_notes="Tester feedback should return to the builder for code fixes.",
        artifacts=["memoryapp-api:latest"],
        deployment_url="https://example.com",
        logs="[INFO] Build succeeded",
    )
    return state


class TestTesterAgent:
    def test_role(self, agent: TesterAgent) -> None:
        assert agent.role == AgentRole.TESTER

    def test_run_populates_test_result(
        self, agent: TesterAgent, state_with_build: WorkflowState
    ) -> None:
        result = agent.run(state_with_build)
        assert result.test_result is not None

    def test_tests_run_parsed(
        self, agent: TesterAgent, state_with_build: WorkflowState
    ) -> None:
        result = agent.run(state_with_build)
        # MockLLM returns 52 tests run
        assert result.test_result.tests_run == 52

    def test_coverage_parsed(
        self, agent: TesterAgent, state_with_build: WorkflowState
    ) -> None:
        result = agent.run(state_with_build)
        assert result.test_result.coverage_percent == 87.0

    def test_iteration_needed(
        self, agent: TesterAgent, state_with_build: WorkflowState
    ) -> None:
        result = agent.run(state_with_build)
        # Mock tester response signals iteration needed
        assert result.test_result.iteration_needed is True
        assert result.test_result.suggested_agent == AgentRole.BUILDER

    def test_message_sent_for_iteration(
        self, agent: TesterAgent, state_with_build: WorkflowState
    ) -> None:
        result = agent.run(state_with_build)
        tester_messages = [
            m for m in result.history if m.sender == AgentRole.TESTER
        ]
        assert len(tester_messages) == 1
        msg = tester_messages[0]
        assert msg.message_type == MessageType.ITERATION_REQUEST
        assert msg.recipient == AgentRole.BUILDER

    def test_raises_without_build_result(self, agent: TesterAgent) -> None:
        state = WorkflowState(original_requirement="Build something")
        with pytest.raises(ValueError, match="BuildResult"):
            agent.run(state)

    def test_parse_response_passed(self) -> None:
        raw = """
TEST SUMMARY:
Tests run   : 10
Tests passed: 10
Tests failed: 0

FAILURES:

COVERAGE: 95%

ITERATION NEEDED: No

SUGGESTED AGENT:

ITERATION REASON:
"""
        result = TesterAgent._parse_response(raw)
        assert result.tests_run == 10
        assert result.tests_passed == 10
        assert result.tests_failed == 0
        assert result.coverage_percent == 95.0
        assert result.iteration_needed is False
        assert result.passed is True

    def test_parse_response_iteration(self) -> None:
        raw = """
TEST SUMMARY:
Tests run   : 5
Tests passed: 3
Tests failed: 2

FAILURES:
- test_a failed.

COVERAGE: 60%

ITERATION NEEDED: Yes

SUGGESTED AGENT: builder

ITERATION REASON:
The build is missing a library.
"""
        result = TesterAgent._parse_response(raw)
        assert result.iteration_needed is True
        assert result.suggested_agent == AgentRole.BUILDER
        assert result.passed is False
        assert len(result.failures) == 1
