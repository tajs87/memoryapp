"""Tests for the Architecture Agent."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agents.architect import ArchitectAgent
from agents.llm import MockLLM
from models import AgentRole, MessageType, RequirementSpec, WorkflowState


@pytest.fixture
def agent() -> ArchitectAgent:
    return ArchitectAgent(llm=MockLLM())


@pytest.fixture
def state_with_spec() -> WorkflowState:
    state = WorkflowState(original_requirement="Build a memory app")
    state.requirement_spec = RequirementSpec(
        original_requirement="Build a memory app",
        clarified_requirements=["Users can create notes", "Data must be persisted"],
        assumptions=["Users are authenticated"],
    )
    return state


class TestArchitectAgent:
    def test_role(self, agent: ArchitectAgent) -> None:
        assert agent.role == AgentRole.ARCHITECT

    def test_run_populates_architecture_spec(
        self, agent: ArchitectAgent, state_with_spec: WorkflowState
    ) -> None:
        result = agent.run(state_with_spec)
        assert result.architecture_spec is not None

    def test_system_overview_non_empty(
        self, agent: ArchitectAgent, state_with_spec: WorkflowState
    ) -> None:
        result = agent.run(state_with_spec)
        assert result.architecture_spec.system_overview != ""

    def test_components_non_empty(
        self, agent: ArchitectAgent, state_with_spec: WorkflowState
    ) -> None:
        result = agent.run(state_with_spec)
        assert len(result.architecture_spec.components) > 0

    def test_message_sent_to_builder(
        self, agent: ArchitectAgent, state_with_spec: WorkflowState
    ) -> None:
        result = agent.run(state_with_spec)
        arch_messages = [
            m for m in result.history if m.sender == AgentRole.ARCHITECT
        ]
        assert len(arch_messages) == 1
        assert arch_messages[0].recipient == AgentRole.BUILDER
        assert arch_messages[0].message_type == MessageType.ARCHITECTURE

    def test_raises_without_requirement_spec(self, agent: ArchitectAgent) -> None:
        state = WorkflowState(original_requirement="Build something")
        with pytest.raises(ValueError, match="RequirementSpec"):
            agent.run(state)

    def test_parse_response_all_sections(self) -> None:
        raw = """
SYSTEM OVERVIEW:
A distributed system.

COMPONENTS:
- API Gateway

TECHNOLOGY STACK:
- Python
- Docker

SCALABILITY:
Horizontal scaling.

PERFORMANCE:
Sub-200ms latency.

DEPLOYMENT:
Kubernetes on AWS.
"""
        spec = ArchitectAgent._parse_response(raw)
        assert "distributed" in spec.system_overview.lower()
        assert len(spec.components) >= 1
        assert "Python" in spec.technology_stack
        assert "Horizontal" in spec.scalability_notes
        assert "200ms" in spec.performance_notes
        assert "Kubernetes" in spec.deployment_strategy
