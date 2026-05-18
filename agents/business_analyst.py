"""Business Analyst Agent.

Responsible for:
- Clarifying ambiguous requirements.
- Identifying assumptions and out-of-scope items.
- Providing structured feedback to guide the rest of the pipeline.
"""

import textwrap

from agents.base_agent import BaseAgent
from agents.parser import parse_sections
from models import (
    AgentRole,
    Message,
    MessageType,
    RequirementSpec,
    WorkflowState,
)


class BusinessAnalystAgent(BaseAgent):
    """First agent in the pipeline – clarifies requirements."""

    role = AgentRole.BUSINESS_ANALYST

    _SYSTEM_PROMPT = textwrap.dedent(
        """\
        [AGENT:business_analyst]
        You are a senior Business Analyst. Your job is to:
        1. Analyse the raw requirement given by the user.
        2. Use relevant public web/product best practices when available and
           cite the sources or standards that most influenced the result.
        3. Restate the requirement as a set of clear, testable, numbered requirements.
        4. Define the main user flows as step-by-step task flows with explicit
           inputs and outputs.
        5. Identify the core inputs the solution must collect.
        6. Identify the key outputs the solution must produce.
        7. Propose a small accessible color palette with explicit color names
           and hex values for the experience.
        8. List any assumptions you are making.
        9. List items you consider out of scope.
        10. Provide concise feedback on gaps or ambiguities.

        Respond in plain text using these exact section headings:
        WEB RESEARCH:
        CLARIFIED REQUIREMENTS:
        USER FLOWS:
        INPUTS:
        OUTPUTS:
        COLOR PALETTE:
        ASSUMPTIONS:
        OUT OF SCOPE:
        FEEDBACK:
        """
    )

    def _execute(self, state: WorkflowState) -> WorkflowState:
        raw = state.original_requirement
        response = self._call_llm(
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=f"Raw requirement:\n{raw}",
        )

        spec = self._parse_response(raw, response)
        state.requirement_spec = spec

        self._record_message(
            state,
            Message(
                sender=AgentRole.BUSINESS_ANALYST,
                recipient=AgentRole.ARCHITECT,
                message_type=MessageType.CLARIFICATION,
                content=response,
                metadata={"original_requirement": raw},
            ),
        )
        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(original: str, response: str) -> RequirementSpec:
        """Parse the LLM text response into a structured RequirementSpec."""
        sections = parse_sections(
            response,
            [
                "WEB RESEARCH",
                "CLARIFIED REQUIREMENTS",
                "USER FLOWS",
                "INPUTS",
                "OUTPUTS",
                "COLOR PALETTE",
                "ASSUMPTIONS",
                "OUT OF SCOPE",
                "FEEDBACK",
            ],
        )

        feedback_lines = sections["FEEDBACK"]
        return RequirementSpec(
            original_requirement=original,
            research_sources=sections["WEB RESEARCH"],
            clarified_requirements=sections["CLARIFIED REQUIREMENTS"],
            user_flows=sections["USER FLOWS"],
            inputs=sections["INPUTS"],
            outputs=sections["OUTPUTS"],
            color_palette=sections["COLOR PALETTE"],
            assumptions=sections["ASSUMPTIONS"],
            out_of_scope=sections["OUT OF SCOPE"],
            feedback=" ".join(feedback_lines),
        )
