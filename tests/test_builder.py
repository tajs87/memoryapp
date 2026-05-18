"""Tests for the Builder/Deploy Agent."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agents.builder import BuilderAgent
from agents.llm import MockLLM
from models import (
    AgentRole,
    ArchitectureSpec,
    MessageType,
    RequirementSpec,
    TestResult as WorkflowTestResult,
    WorkflowState,
)


@pytest.fixture
def agent() -> BuilderAgent:
    return BuilderAgent(llm=MockLLM())


@pytest.fixture
def state_with_arch() -> WorkflowState:
    state = WorkflowState(original_requirement="Build a memory app")
    state.requirement_spec = RequirementSpec(
        original_requirement="Build a memory app",
        clarified_requirements=["Users can create notes", "Data must be persisted"],
        user_flows=["Create memory -> save -> view memory"],
        inputs=["Memory title", "Memory content"],
        outputs=["Saved memory", "Search results"],
    )
    state.architecture_spec = ArchitectureSpec(
        architectural_requirements=["Authenticated CRUD APIs", "Searchable memory records"],
        system_overview="Three-tier web app",
        components=[{"description": "API Gateway"}, {"description": "FastAPI service"}],
        authentication_strategy="JWT",
        user_flows=["Authenticate -> create memory -> search memory"],
        styling_guidance=["Use accessible semantic status colors"],
        technology_stack=["Python", "FastAPI", "PostgreSQL", "Docker"],
        scalability_notes="Horizontal app scaling",
        performance_notes="Cache frequent reads",
        deployment_strategy="Kubernetes on AWS",
    )
    state.test_result = WorkflowTestResult(
        passed=False,
        tests_run=8,
        tests_passed=6,
        tests_failed=2,
        failures=["test_search_unicode failed", "test_concurrent_write failed"],
        coverage_percent=82.0,
        iteration_needed=True,
        suggested_agent=AgentRole.BUILDER,
        iteration_reason="Builder should fix implementation and regression gaps.",
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

    def test_additional_build_sections_non_empty(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        build = result.build_result
        assert build.implementation_summary != ""
        assert len(build.completed_requirements) > 0
        assert len(build.unit_tests) > 0
        assert len(build.regression_tests) > 0
        assert build.collaboration_notes != ""
        assert build.container_details != ""
        assert len(build.testing_urls) > 0

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

    def test_system_prompt_requires_repo_sync(self, agent: BuilderAgent) -> None:
        prompt = agent._SYSTEM_PROMPT
        assert "First create a GitHub repository" in prompt
        assert "business analyst, architect, and tester" in prompt

    def test_mock_response_mentions_repo_sync(
        self, agent: BuilderAgent, state_with_arch: WorkflowState
    ) -> None:
        result = agent.run(state_with_arch)
        build = result.build_result
        assert "github repository" in build.implementation_summary.lower()
        assert "updated" in build.collaboration_notes.lower()

    def test_raises_without_architecture_spec(self, agent: BuilderAgent) -> None:
        state = WorkflowState(original_requirement="Build something")
        with pytest.raises(ValueError, match="ArchitectureSpec"):
            agent.run(state)

    def test_parse_response_failure(self) -> None:
        raw = """
BUILD STATUS: FAILURE

IMPLEMENTATION:
Build did not complete.

REQUIREMENTS COVERAGE:

UNIT TESTS:

REGRESSION TESTS:

COLLABORATION:
Escalate only if requirement or architecture guidance is missing.

CONTAINER:
Container image was not built.

ARTIFACTS:

DEPLOYMENT URL:

TEST URLS:

LOGS:
[ERROR] Compilation failed.

ERRORS:
- Missing dependency X.
"""
        result = BuilderAgent._parse_response(raw)
        assert result.success is False
        assert result.implementation_summary == "Build did not complete."
        assert result.container_details == "Container image was not built."
        assert len(result.errors) == 1

    def test_parse_response_success(self) -> None:
        raw = """
BUILD STATUS: SUCCESS

IMPLEMENTATION:
Delivered the application.

REQUIREMENTS COVERAGE:
- Implemented authenticated CRUD.

UNIT TESTS:
- test_create_memory

REGRESSION TESTS:
- test_unicode_search

COLLABORATION:
Tester feedback should return to the builder for code fixes.

CONTAINER:
Deployed app:latest as a container to staging.

ARTIFACTS:
- app:latest

DEPLOYMENT URL: https://example.com

TEST URLS:
- https://example.com/health
- https://example.com/ui

LOGS:
[INFO] Done.

ERRORS:
"""
        result = BuilderAgent._parse_response(raw)
        assert result.success is True
        assert result.implementation_summary == "Delivered the application."
        assert len(result.completed_requirements) == 1
        assert len(result.unit_tests) == 1
        assert len(result.regression_tests) == 1
        assert "builder" in result.collaboration_notes.lower()
        assert "container" in result.container_details.lower()
        assert result.deployment_url == "https://example.com"
        assert result.testing_urls == [
            "https://example.com/health",
            "https://example.com/ui",
        ]
