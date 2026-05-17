"""Tester Agent.

Responsible for:
- Verifying the build output against the clarified requirements.
- Reporting test results (pass/fail, coverage).
- Deciding whether an iteration is needed and which agent should be invoked.
"""

import textwrap

from agents.base_agent import BaseAgent
from agents.parser import parse_sections
from models import (
    AgentRole,
    Message,
    MessageType,
    TestResult,
    WorkflowState,
)

_AGENT_ROLE_MAP: dict[str, AgentRole] = {
    "business_analyst": AgentRole.BUSINESS_ANALYST,
    "architect": AgentRole.ARCHITECT,
    "builder": AgentRole.BUILDER,
    "tester": AgentRole.TESTER,
}


class TesterAgent(BaseAgent):
    """Fourth agent in the pipeline – tests, validates and drives iteration."""

    role = AgentRole.TESTER

    _SYSTEM_PROMPT = textwrap.dedent(
        """\
        [AGENT:tester]
        You are a senior QA Engineer. Given the original requirements and the
        result of a build/deployment, evaluate whether the application meets all
        requirements. Your output must include:
        1. A test summary (tests run, passed, failed).
        2. A list of specific test failures (if any).
        3. An estimated test coverage percentage.
        4. Whether another iteration is needed (ITERATION NEEDED: Yes/No).
        5. If iteration is needed, which agent should be called next:
           business_analyst, architect, or builder.
        6. The reason an iteration is needed.

        Respond in plain text using these exact section headings:
        TEST SUMMARY:
        FAILURES:
        COVERAGE:
        ITERATION NEEDED:
        SUGGESTED AGENT:
        ITERATION REASON:
        """
    )

    def _execute(self, state: WorkflowState) -> WorkflowState:
        if state.build_result is None:
            raise ValueError(
                "TesterAgent requires a BuildResult in state. "
                "Run BuilderAgent first."
            )

        requirements_text = ""
        if state.requirement_spec:
            requirements_text = "\n".join(
                f"- {r}" for r in state.requirement_spec.clarified_requirements
            )

        build = state.build_result
        build_summary = (
            f"Build success: {build.success}\n"
            f"Artifacts: {', '.join(build.artifacts)}\n"
            f"Deployment URL: {build.deployment_url or 'N/A'}\n"
            f"Logs:\n{build.logs}\n"
            f"Errors: {', '.join(build.errors) or 'None'}"
        )

        user_prompt = (
            f"Requirements:\n{requirements_text or state.original_requirement}\n\n"
            f"Build result:\n{build_summary}"
        )

        response = self._call_llm(
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        result = self._parse_response(response)
        state.test_result = result

        self._record_message(
            state,
            Message(
                sender=AgentRole.TESTER,
                recipient=result.suggested_agent or AgentRole.TESTER,
                message_type=(
                    MessageType.ITERATION_REQUEST
                    if result.iteration_needed
                    else MessageType.TEST_RESULT
                ),
                content=response,
                metadata={
                    "passed": result.passed,
                    "iteration_needed": result.iteration_needed,
                    "suggested_agent": (
                        result.suggested_agent.value
                        if result.suggested_agent
                        else None
                    ),
                },
            ),
        )
        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response: str) -> TestResult:
        sections = parse_sections(
            response,
            ["TEST SUMMARY", "FAILURES", "COVERAGE", "ITERATION NEEDED", "SUGGESTED AGENT", "ITERATION REASON"],
        )

        # Parse test counts from summary lines such as "Tests run   : 52"
        tests_run = tests_passed = tests_failed = 0
        for line in sections["TEST SUMMARY"]:
            lower = line.lower()
            try:
                val = int(line.split(":")[-1].strip().split()[0])
            except (ValueError, IndexError):
                val = 0
            if "run" in lower:
                tests_run = val
            elif "passed" in lower:
                tests_passed = val
            elif "failed" in lower:
                tests_failed = val

        # Coverage
        coverage = 0.0
        for line in sections["COVERAGE"]:
            try:
                coverage = float(line.replace("%", "").strip().split()[0])
                break
            except (ValueError, IndexError):
                pass

        # Iteration needed?
        iteration_line = " ".join(sections["ITERATION NEEDED"]).lower()
        iteration_needed = "yes" in iteration_line

        # Suggested agent
        agent_line = " ".join(sections["SUGGESTED AGENT"]).lower().strip()
        suggested_agent: AgentRole | None = None
        for key, role in _AGENT_ROLE_MAP.items():
            if key in agent_line:
                suggested_agent = role
                break

        passed = (not iteration_needed) and (tests_failed == 0)

        return TestResult(
            passed=passed,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            failures=sections["FAILURES"],
            coverage_percent=coverage,
            iteration_needed=iteration_needed,
            suggested_agent=suggested_agent,
            iteration_reason=" ".join(sections["ITERATION REASON"]),
        )
