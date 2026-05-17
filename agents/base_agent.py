"""Base agent class shared by all specialised agents."""

from abc import ABC, abstractmethod

from agents.llm import BaseLLM, get_llm
from models import AgentRole, Message, WorkflowState


class BaseAgent(ABC):
    """Abstract base for every agent in the pipeline."""

    role: AgentRole

    def __init__(self, llm: BaseLLM | None = None) -> None:
        self._llm: BaseLLM = llm if llm is not None else get_llm()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, state: WorkflowState) -> WorkflowState:
        """
        Execute the agent's work on *state* and return the updated state.

        Subclasses implement ``_execute`` which performs the actual work.
        This wrapper records messages in ``state.history``.
        """
        state = self._execute(state)
        return state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        return self._llm.complete(system_prompt, user_prompt)

    def _record_message(
        self,
        state: WorkflowState,
        message: Message,
    ) -> None:
        state.history.append(message)

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abstractmethod
    def _execute(self, state: WorkflowState) -> WorkflowState:
        """Perform the agent's specialised work and return updated state."""
