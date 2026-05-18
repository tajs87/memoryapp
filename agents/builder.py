"""Builder/Deploy Agent.

Responsible for:
- Translating the architecture specification into a concrete build plan.
- Simulating (or orchestrating) the build and deployment process.
- Reporting build artifacts, deployment URL and any errors.
"""

import textwrap

from agents.base_agent import BaseAgent
from agents.parser import parse_sections
from models import (
    AgentRole,
    BuildResult,
    Message,
    MessageType,
    WorkflowState,
)


class BuilderAgent(BaseAgent):
    """Third agent in the pipeline – builds and deploys the application."""

    role = AgentRole.BUILDER

    _SYSTEM_PROMPT = textwrap.dedent(
        """\
        [AGENT:builder]
        You are a senior Builder / Full-Stack Engineer. Given the business
        requirements, system architecture, and any tester feedback, describe in
        detail how you would implement, test, and deploy the application. Your
        output must include:
        1. Whether the build succeeded (BUILD STATUS: SUCCESS or FAILURE).
        2. A concise implementation summary covering the delivered application.
        3. A list of requirements completed from the business analyst and
           architect specifications.
        4. The unit tests created or executed.
        5. The regression tests created or executed.
        6. How the builder incorporated architect guidance and tester feedback,
           and when to loop back to business analyst or architect.
        7. First create a GitHub repository for the implementation if one does
           not already exist, then keep it updated with commits that include the
           latest outputs from the business analyst, architect, and tester.
        8. How the solution is deployed in a container, including the image or
           runtime details that testers should use.
        9. A list of build artifacts produced.
        10. The primary deployment URL (or placeholder if not yet available).
        11. The URLs testers should use, such as health, API base, UI, or other
            relevant endpoints.
        12. Relevant build/deploy log lines.
        13. Any errors encountered.

        Respond in plain text using these exact section headings:
        BUILD STATUS:
        IMPLEMENTATION:
        REQUIREMENTS COVERAGE:
        UNIT TESTS:
        REGRESSION TESTS:
        COLLABORATION:
        CONTAINER:
        ARTIFACTS:
        DEPLOYMENT URL:
        TEST URLS:
        LOGS:
        ERRORS:
        """
    )

    def _execute(self, state: WorkflowState) -> WorkflowState:
        if state.architecture_spec is None:
            raise ValueError(
                "BuilderAgent requires an ArchitectureSpec in state. "
                "Run ArchitectAgent first."
            )

        arch = state.architecture_spec
        requirement_spec = state.requirement_spec
        components_text = "\n".join(
            f"- {c.get('description', '')}" for c in arch.components
        )
        requirements_text = (
            "\n".join(f"- {item}" for item in requirement_spec.clarified_requirements)
            if requirement_spec and requirement_spec.clarified_requirements
            else f"- {state.original_requirement}"
        )
        requirement_flows = (
            "\n".join(f"- {item}" for item in requirement_spec.user_flows)
            if requirement_spec and requirement_spec.user_flows
            else "- No explicit business analyst flows provided."
        )
        requirement_inputs = (
            "\n".join(f"- {item}" for item in requirement_spec.inputs)
            if requirement_spec and requirement_spec.inputs
            else "- No explicit business analyst inputs provided."
        )
        requirement_outputs = (
            "\n".join(f"- {item}" for item in requirement_spec.outputs)
            if requirement_spec and requirement_spec.outputs
            else "- No explicit business analyst outputs provided."
        )
        architect_requirements = (
            "\n".join(f"- {item}" for item in arch.architectural_requirements)
            if arch.architectural_requirements
            else "- No explicit architectural requirements provided."
        )
        architect_flows = (
            "\n".join(f"- {item}" for item in arch.user_flows)
            if arch.user_flows
            else "- No explicit architect flows provided."
        )
        tester_feedback = "No tester feedback yet."
        if state.test_result:
            failures_text = (
                "\n".join(f"- {item}" for item in state.test_result.failures)
                if state.test_result.failures
                else "- No explicit tester failures recorded."
            )
            tester_feedback = (
                f"Iteration needed: {state.test_result.iteration_needed}\n"
                f"Suggested agent: "
                f"{state.test_result.suggested_agent.value if state.test_result.suggested_agent else 'none'}\n"
                f"Iteration reason: {state.test_result.iteration_reason or 'None'}\n"
                f"Failures:\n{failures_text}"
            )
        user_prompt = (
            f"Original Requirement:\n- {state.original_requirement}\n\n"
            f"Business Analyst Requirements:\n{requirements_text}\n\n"
            f"Business Analyst User Flows:\n{requirement_flows}\n\n"
            f"Business Analyst Inputs:\n{requirement_inputs}\n\n"
            f"Business Analyst Outputs:\n{requirement_outputs}\n\n"
            f"Architectural Requirements:\n{architect_requirements}\n\n"
            f"System Overview: {arch.system_overview}\n\n"
            f"Components:\n{components_text}\n\n"
            f"Technology Stack: {', '.join(arch.technology_stack)}\n\n"
            f"Authentication Strategy: {arch.authentication_strategy or 'Not provided'}\n\n"
            f"Architect User Flows:\n{architect_flows}\n\n"
            f"Styling Guidance:\n"
            + (
                "\n".join(f"- {item}" for item in arch.styling_guidance)
                if arch.styling_guidance
                else "- No explicit styling guidance provided."
            )
            + "\n\n"
            + f"Scalability Notes: {arch.scalability_notes or 'Not provided'}\n\n"
            + f"Performance Notes: {arch.performance_notes or 'Not provided'}\n\n"
            + f"Deployment Strategy: {arch.deployment_strategy}\n\n"
            + f"Tester Feedback:\n{tester_feedback}"
        )

        response = self._call_llm(
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        result = self._parse_response(response)
        state.build_result = result

        self._record_message(
            state,
            Message(
                sender=AgentRole.BUILDER,
                recipient=AgentRole.TESTER,
                message_type=MessageType.BUILD_RESULT,
                content=response,
                metadata={"success": result.success},
            ),
        )
        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response: str) -> BuildResult:
        sections = parse_sections(
            response,
            [
                "BUILD STATUS",
                "IMPLEMENTATION",
                "REQUIREMENTS COVERAGE",
                "UNIT TESTS",
                "REGRESSION TESTS",
                "COLLABORATION",
                "CONTAINER",
                "ARTIFACTS",
                "DEPLOYMENT URL",
                "TEST URLS",
                "LOGS",
                "ERRORS",
            ],
        )

        status_line = " ".join(sections["BUILD STATUS"]).upper()
        success = "SUCCESS" in status_line

        url_parts = sections["DEPLOYMENT URL"]
        deployment_url = url_parts[0] if url_parts else None

        return BuildResult(
            success=success,
            implementation_summary="\n".join(sections["IMPLEMENTATION"]),
            completed_requirements=sections["REQUIREMENTS COVERAGE"],
            unit_tests=sections["UNIT TESTS"],
            regression_tests=sections["REGRESSION TESTS"],
            collaboration_notes="\n".join(sections["COLLABORATION"]),
            container_details="\n".join(sections["CONTAINER"]),
            artifacts=sections["ARTIFACTS"],
            deployment_url=deployment_url,
            testing_urls=sections["TEST URLS"],
            logs="\n".join(sections["LOGS"]),
            errors=sections["ERRORS"],
        )
