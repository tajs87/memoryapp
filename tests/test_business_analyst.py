"""Tests for the Business Analyst Agent."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agents.business_analyst import BusinessAnalystAgent
from agents.llm import MockLLM
from models import AgentRole, MessageType, WorkflowState


@pytest.fixture
def agent() -> BusinessAnalystAgent:
    return BusinessAnalystAgent(llm=MockLLM())


@pytest.fixture
def state() -> WorkflowState:
    return WorkflowState(original_requirement="Build a memory management app")


class TestBusinessAnalystAgent:
    def test_role(self, agent: BusinessAnalystAgent) -> None:
        assert agent.role == AgentRole.BUSINESS_ANALYST

    def test_run_populates_requirement_spec(
        self, agent: BusinessAnalystAgent, state: WorkflowState
    ) -> None:
        result = agent.run(state)
        assert result.requirement_spec is not None

    def test_clarified_requirements_non_empty(
        self, agent: BusinessAnalystAgent, state: WorkflowState
    ) -> None:
        result = agent.run(state)
        assert len(result.requirement_spec.clarified_requirements) > 0

    def test_additional_requirement_sections_non_empty(
        self, agent: BusinessAnalystAgent, state: WorkflowState
    ) -> None:
        result = agent.run(state)
        spec = result.requirement_spec
        assert len(spec.research_sources) > 0
        assert len(spec.user_flows) > 0
        assert len(spec.inputs) > 0
        assert len(spec.outputs) > 0
        assert len(spec.color_palette) > 0

    def test_original_requirement_preserved(
        self, agent: BusinessAnalystAgent, state: WorkflowState
    ) -> None:
        result = agent.run(state)
        assert result.requirement_spec.original_requirement == state.original_requirement

    def test_message_recorded_in_history(
        self, agent: BusinessAnalystAgent, state: WorkflowState
    ) -> None:
        result = agent.run(state)
        assert len(result.history) == 1
        msg = result.history[0]
        assert msg.sender == AgentRole.BUSINESS_ANALYST
        assert msg.recipient == AgentRole.ARCHITECT
        assert msg.message_type == MessageType.CLARIFICATION

    def test_parse_response_sections(self) -> None:
        raw_response = """
WEB RESEARCH:
- WCAG 2.2 use-of-color guidance.

CLARIFIED REQUIREMENTS:
- The system shall do X.
- The system shall do Y.

USER FLOWS:
- Create memory: open form -> submit -> confirmation.

INPUTS:
- Memory title.

OUTPUTS:
- Saved memory record.

COLOR PALETTE:
- Primary blue: #2563EB.

ASSUMPTIONS:
- Users are authenticated.

OUT OF SCOPE:
- Payment processing.

FEEDBACK:
Overall requirements are clear.
"""
        spec = BusinessAnalystAgent._parse_response("original", raw_response)
        assert len(spec.research_sources) == 1
        assert len(spec.clarified_requirements) == 2
        assert len(spec.user_flows) == 1
        assert len(spec.inputs) == 1
        assert len(spec.outputs) == 1
        assert len(spec.color_palette) == 1
        assert len(spec.assumptions) == 1
        assert len(spec.out_of_scope) == 1
        assert "clear" in spec.feedback.lower()

    def test_parse_response_empty_sections(self) -> None:
        spec = BusinessAnalystAgent._parse_response("req", "No structured content here.")
        assert spec.clarified_requirements == []
        assert spec.research_sources == []
        assert spec.user_flows == []
        assert spec.inputs == []
        assert spec.outputs == []
        assert spec.color_palette == []
        assert spec.assumptions == []
