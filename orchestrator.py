"""Multi-agent Orchestrator.

Coordinates the four agents in order:
  1. BusinessAnalystAgent  – clarify requirements
  2. ArchitectAgent        – design architecture
  3. BuilderAgent          – build and deploy
  4. TesterAgent           – test; iterate if needed

The TesterAgent may request another iteration by specifying a *suggested_agent*.
The orchestrator then re-runs the pipeline from that agent onwards, up to
``MAX_ITERATIONS`` times.
"""

import logging

import config
from agents import (
    ArchitectAgent,
    BuilderAgent,
    BusinessAnalystAgent,
    TesterAgent,
)
from agents.base_agent import BaseAgent
from agents.llm import BaseLLM, get_llm
from models import AgentRole, WorkflowState

logger = logging.getLogger(__name__)


class Orchestrator:
    """Runs and coordinates all agents."""

    # Maps each AgentRole to its position in the pipeline.
    _PIPELINE_ORDER: list[AgentRole] = [
        AgentRole.BUSINESS_ANALYST,
        AgentRole.ARCHITECT,
        AgentRole.BUILDER,
        AgentRole.TESTER,
    ]

    def __init__(self, llm: BaseLLM | None = None) -> None:
        shared_llm: BaseLLM = llm if llm is not None else get_llm()
        self._agents: dict[AgentRole, BaseAgent] = {
            AgentRole.BUSINESS_ANALYST: BusinessAnalystAgent(shared_llm),
            AgentRole.ARCHITECT: ArchitectAgent(shared_llm),
            AgentRole.BUILDER: BuilderAgent(shared_llm),
            AgentRole.TESTER: TesterAgent(shared_llm),
        }
        self._max_iterations: int = config.MAX_ITERATIONS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, requirement: str) -> WorkflowState:
        """
        Execute the full pipeline for *requirement*.

        Returns the final :class:`WorkflowState` after all iterations.
        """
        state = WorkflowState(original_requirement=requirement)
        state = self._run_from(state, start_role=AgentRole.BUSINESS_ANALYST)
        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_from(
        self, state: WorkflowState, start_role: AgentRole
    ) -> WorkflowState:
        """Run the pipeline starting at *start_role* and handle iterations."""
        start_idx = self._PIPELINE_ORDER.index(start_role)

        for role in self._PIPELINE_ORDER[start_idx:]:
            agent = self._agents[role]
            logger.info("[%s] Running agent…", role.value)
            state = agent.run(state)
            logger.info("[%s] Done.", role.value)

        # After the tester has run, check whether an iteration is requested.
        while (
            state.test_result is not None
            and state.test_result.iteration_needed
            and state.iteration_count < self._max_iterations
        ):
            state.iteration_count += 1
            suggested = state.test_result.suggested_agent

            logger.info(
                "[orchestrator] Iteration %d/%d requested. "
                "Restarting from agent: %s",
                state.iteration_count,
                self._max_iterations,
                suggested.value if suggested else "architect",
            )

            restart_role = suggested if suggested else AgentRole.ARCHITECT
            state = self._run_from(state, start_role=restart_role)

        return state
