"""FastAPI server for interacting with the multi-agent workflow."""

from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents import ArchitectAgent, BuilderAgent, BusinessAnalystAgent, TesterAgent
from agents.base_agent import BaseAgent
from agents.llm import get_llm
from models import AgentRole, WorkflowState
from orchestrator import Orchestrator

app = FastAPI(title="memoryapp API", version="1.0.0")

_AGENT_DESCRIPTIONS: Dict[AgentRole, str] = {
    AgentRole.BUSINESS_ANALYST: "Clarifies requirements and assumptions.",
    AgentRole.ARCHITECT: "Designs architecture and deployment strategy.",
    AgentRole.BUILDER: "Builds and deploys the solution.",
    AgentRole.TESTER: "Tests output and requests iteration if needed.",
}


class AgentInfo(BaseModel):
    role: AgentRole
    description: str


class WorkflowRunRequest(BaseModel):
    requirement: str


class ProgressEvent(BaseModel):
    agent: AgentRole
    iteration: int
    message_count: int
    message_type: str | None = None
    recipient: AgentRole | None = None


class WorkflowRunResponse(BaseModel):
    state: WorkflowState
    progress: List[ProgressEvent]


def _build_agent(role: AgentRole) -> BaseAgent:
    llm = get_llm()
    if role == AgentRole.BUSINESS_ANALYST:
        return BusinessAnalystAgent(llm=llm)
    if role == AgentRole.ARCHITECT:
        return ArchitectAgent(llm=llm)
    if role == AgentRole.BUILDER:
        return BuilderAgent(llm=llm)
    if role == AgentRole.TESTER:
        return TesterAgent(llm=llm)
    raise ValueError(f"Unsupported role: {role.value}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agents", response_model=List[AgentInfo])
def list_agents() -> List[AgentInfo]:
    return [
        AgentInfo(role=role, description=description)
        for role, description in _AGENT_DESCRIPTIONS.items()
    ]


@app.post("/workflow/run", response_model=WorkflowRunResponse)
def run_workflow(payload: WorkflowRunRequest) -> WorkflowRunResponse:
    orchestrator = Orchestrator()
    progress: List[ProgressEvent] = []

    def _on_progress(role: AgentRole, state: WorkflowState) -> None:
        latest = next((m for m in reversed(state.history) if m.sender == role), None)
        progress.append(
            ProgressEvent(
                agent=role,
                iteration=state.iteration_count,
                message_count=len(state.history),
                message_type=(latest.message_type.value if latest else None),
                recipient=(latest.recipient if latest else None),
            )
        )

    state = orchestrator.run(payload.requirement, progress_callback=_on_progress)
    return WorkflowRunResponse(state=state, progress=progress)


@app.post("/agents/{agent_role}/run", response_model=WorkflowState)
def run_single_agent(agent_role: str, state: WorkflowState) -> WorkflowState:
    try:
        role = AgentRole(agent_role)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent role '{agent_role}'.",
        ) from exc

    agent = _build_agent(role)
    return agent.run(state)
