"""Tests for the Builder/Deploy Agent."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agents.builder import BuilderAgent
from agents.llm import MockLLM
from models import AgentRole, ArchitectureSpec, MessageType, WorkflowState


@pytest.fixture
def agent() -> BuilderAgent:
    return BuilderAgent(llm=MockLLM())


@pytest.fixture
def state_with_arch() -> WorkflowState:
    state = WorkflowState(original_requirement="Build a memory app")
    state.architecture_spec = ArchitectureSpec(
        system_overview="Three-tier web app",
        components=[{"description": "API Gateway"}, {"description": "FastAPI service"}],
        technology_stack=["Python", "FastAPI", "PostgreSQL", "Docker"],
        deployment_strategy="Kubernetes on AWS",
    )
    return state


class TestBuilderAgent:
    def test_role(self, agent: BuilderAgent) -> None:
        assert agent.role == AgentRole.BUILDER

    def test_run_populates_build_result(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        assert result.build_result is not None

    def test_build_success_flag(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        # Mock LLM returns SUCCESS – assert the flag is parsed correctly.
        assert result.build_result.success is True

    def test_artifacts_non_empty(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        assert len(result.build_result.artifacts) > 0

    def test_deployment_url_present(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        assert result.build_result.deployment_url is not None

    def test_message_sent_to_tester(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        builder_messages = [
            m for m in result.history if m.sender == AgentRole.BUILDER
        ]
        assert len(builder_messages) == 1
        assert builder_messages[0].recipient == AgentRole.TESTER
        assert builder_messages[0].message_type == MessageType.BUILD_RESULT

    def test_raises_without_architecture_spec(self, agent: BuilderAgent) -> None:
        state = WorkflowState(original_requirement="Build something")
        with pytest.raises(ValueError, match="ArchitectureSpec"):
            agent.run(state)

    def test_parse_response_failure(self) -> None:
        raw = """
BUILD STATUS: FAILURE

ARTIFACTS:

DEPLOYMENT URL:

LOGS:
[ERROR] Compilation failed.

ERRORS:
- Missing dependency X.
"""
        result = BuilderAgent._parse_response(raw)
        assert result.success is False
        assert len(result.errors) == 1

    def test_parse_response_success(self) -> None:
        raw = """
BUILD STATUS: SUCCESS

ARTIFACTS:
- app:latest

DEPLOYMENT URL: https://example.com

LOGS:
[INFO] Done.

ERRORS:
"""
        result = BuilderAgent._parse_response(raw)
        assert result.success is True
        assert result.deployment_url == "https://example.com"
