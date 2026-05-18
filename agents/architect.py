"""Architecture Agent.

Responsible for:
- Designing a system architecture that satisfies the clarified requirements.
- Addressing scalability and performance concerns explicitly.
- Proposing a technology stack and deployment strategy.
"""

import textwrap

from agents.base_agent import BaseAgent
from agents.parser import parse_sections
from models import (
    AgentRole,
    ArchitectureSpec,
    Message,
    MessageType,
    WorkflowState,
)


class ArchitectAgent(BaseAgent):
    """Second agent in the pipeline – creates the system architecture."""

    role = AgentRole.ARCHITECT

    _SYSTEM_PROMPT = textwrap.dedent(
        """\
        [AGENT:architect]
        You are a principal Software Architect. Given a set of requirements, design
        a production-ready system architecture. You must:
        1. Provide a high-level system overview.
        2. List each major component and its responsibility.
        3. Specify the technology stack.
        4. Explain scalability considerations.
        5. Explain performance considerations.
        6. Describe the deployment strategy.

        Respond in plain text using these exact section headings:
        SYSTEM OVERVIEW:
        COMPONENTS:
        TECHNOLOGY STACK:
        SCALABILITY:
        PERFORMANCE:
        DEPLOYMENT:
        """
    )

    def _execute(self, state: WorkflowState) -> WorkflowState:
        if state.requirement_spec is None:
            raise ValueError(
                "ArchitectAgent requires a RequirementSpec in state. "
                "Run BusinessAnalystAgent first."
            )

        spec = state.requirement_spec
        requirements_text = "\n".join(
            f"- {r}" for r in spec.clarified_requirements
        ) or spec.original_requirement

        user_prompt = (
            f"Requirements:\n{requirements_text}\n\n"
            f"Web research:\n"
            + "\n".join(f"- {source}" for source in spec.research_sources)
            + "\n\n"
            + f"User flows:\n"
            + "\n".join(f"- {flow}" for flow in spec.user_flows)
            + "\n\n"
            + f"Inputs:\n"
            + "\n".join(f"- {item}" for item in spec.inputs)
            + "\n\n"
            + f"Outputs:\n"
            + "\n".join(f"- {item}" for item in spec.outputs)
            + "\n\n"
            + f"Color palette:\n"
            + "\n".join(f"- {color}" for color in spec.color_palette)
            + "\n\n"
            + f"Assumptions:\n"
            + "\n".join(f"- {a}" for a in spec.assumptions)
        )

        response = self._call_llm(
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        arch = self._parse_response(response)
        state.architecture_spec = arch

        self._record_message(
            state,
            Message(
                sender=AgentRole.ARCHITECT,
                recipient=AgentRole.BUILDER,
                message_type=MessageType.ARCHITECTURE,
                content=response,
            ),
        )
        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response: str) -> ArchitectureSpec:
        sections = parse_sections(
            response,
            ["SYSTEM OVERVIEW", "COMPONENTS", "TECHNOLOGY STACK", "SCALABILITY", "PERFORMANCE", "DEPLOYMENT"],
        )

        def _join(key: str) -> str:
            return " ".join(sections[key])

        # Parse components – each line becomes its own dict entry.
        components: list[dict[str, str]] = [
            {"description": line}
            for line in sections["COMPONENTS"]
        ]

        return ArchitectureSpec(
            system_overview=_join("SYSTEM OVERVIEW"),
            components=components,
            technology_stack=sections["TECHNOLOGY STACK"],
            scalability_notes=_join("SCALABILITY"),
            performance_notes=_join("PERFORMANCE"),
            deployment_strategy=_join("DEPLOYMENT"),
        )
