"""Models shared across the multi-agent system."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    BUSINESS_ANALYST = "business_analyst"
    ARCHITECT = "architect"
    BUILDER = "builder"
    TESTER = "tester"


class MessageType(str, Enum):
    REQUIREMENT = "requirement"
    CLARIFICATION = "clarification"
    ARCHITECTURE = "architecture"
    BUILD_RESULT = "build_result"
    TEST_RESULT = "test_result"
    ITERATION_REQUEST = "iteration_request"


class Message(BaseModel):
    """A message passed between agents."""

    sender: AgentRole
    recipient: AgentRole
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RequirementSpec(BaseModel):
    """Refined requirements produced by the Business Analyst Agent."""

    original_requirement: str
    clarified_requirements: List[str] = Field(default_factory=list)
    research_sources: List[str] = Field(default_factory=list)
    user_flows: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    color_palette: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)
    feedback: str = ""


class ArchitectureSpec(BaseModel):
    """Architecture document produced by the Architecture Agent."""

    research_sources: List[str] = Field(default_factory=list)
    architectural_requirements: List[str] = Field(default_factory=list)
    system_overview: str
    components: List[Dict[str, str]] = Field(default_factory=list)
    authentication_strategy: str = ""
    user_journeys: List[str] = Field(default_factory=list)
    user_flows: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    styling_guidance: List[str] = Field(default_factory=list)
    scalability_notes: str = ""
    performance_notes: str = ""
    technology_stack: List[str] = Field(default_factory=list)
    deployment_strategy: str = ""


class BuildResult(BaseModel):
    """Result produced by the Builder/Deploy Agent."""

    success: bool
    implementation_summary: str = ""
    completed_requirements: List[str] = Field(default_factory=list)
    unit_tests: List[str] = Field(default_factory=list)
    regression_tests: List[str] = Field(default_factory=list)
    collaboration_notes: str = ""
    artifacts: List[str] = Field(default_factory=list)
    deployment_url: Optional[str] = None
    logs: str = ""
    errors: List[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Result produced by the Tester Agent."""

    passed: bool
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    failures: List[str] = Field(default_factory=list)
    coverage_percent: float = 0.0
    iteration_needed: bool = False
    suggested_agent: Optional[AgentRole] = None
    iteration_reason: str = ""


class WorkflowState(BaseModel):
    """Tracks state as it flows through the pipeline."""

    original_requirement: str
    requirement_spec: Optional[RequirementSpec] = None
    architecture_spec: Optional[ArchitectureSpec] = None
    build_result: Optional[BuildResult] = None
    test_result: Optional[TestResult] = None
    iteration_count: int = 0
    history: List[Message] = Field(default_factory=list)
