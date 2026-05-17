"""Builder/Deploy Agent.

Responsible for:
- Translating the architecture specification into a concrete build plan.
- Simulating (or orchestrating) the build and deployment process.
- Reporting build artefacts, deployment URL and any errors.
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
        You are a senior DevOps / Build Engineer. Given a system architecture
        specification, describe in detail how you would build and deploy the
        described application. Your output must include:
        1. Whether the build succeeded (BUILD STATUS: SUCCESS or FAILURE).
        2. A list of build artefacts produced.
        3. The deployment URL (or placeholder if not yet available).
        4. Relevant build/deploy log lines.
        5. Any errors encountered.

        Respond in plain text using these exact section headings:
        BUILD STATUS:
        ARTIFACTS:
        DEPLOYMENT URL:
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
        components_text = "\n".join(
            f"- {c.get('description', '')}" for c in arch.components
        )
        user_prompt = (
            f"System Overview: {arch.system_overview}\n\n"
            f"Components:\n{components_text}\n\n"
            f"Technology Stack: {', '.join(arch.technology_stack)}\n\n"
            f"Deployment Strategy: {arch.deployment_strategy}"
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
            ["BUILD STATUS", "ARTIFACTS", "DEPLOYMENT URL", "LOGS", "ERRORS"],
        )

        status_line = " ".join(sections["BUILD STATUS"]).upper()
        success = "SUCCESS" in status_line

        url_parts = sections["DEPLOYMENT URL"]
        deployment_url = url_parts[0] if url_parts else None

        return BuildResult(
            success=success,
            artifacts=sections["ARTIFACTS"],
            deployment_url=deployment_url,
            logs="\n".join(sections["LOGS"]),
            errors=sections["ERRORS"],
        )
