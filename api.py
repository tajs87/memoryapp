"""FastAPI server for interacting with the multi-agent workflow."""

import json
import queue
import threading
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from agents import ArchitectAgent, BuilderAgent, BusinessAnalystAgent, TesterAgent
from agents.base_agent import BaseAgent
from agents.llm import get_llm
from models import AgentRole, MessageType, WorkflowState
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
    requirement: str = Field(min_length=1, max_length=2000)


class ProgressEvent(BaseModel):
    agent: AgentRole
    iteration: int
    message_count: int
    message_type: MessageType | None = None
    recipient: AgentRole | None = None


class WorkflowRunResponse(BaseModel):
    state: WorkflowState
    progress: List[ProgressEvent]


def _build_progress_event(role: AgentRole, state: WorkflowState) -> ProgressEvent:
    latest = None
    for idx in range(len(state.history) - 1, -1, -1):
        message = state.history[idx]
        if message.sender == role:
            latest = message
            break
    return ProgressEvent(
        agent=role,
        iteration=state.iteration_count,
        message_count=len(state.history),
        message_type=(latest.message_type if latest else None),
        recipient=(latest.recipient if latest else None),
    )


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
        progress.append(_build_progress_event(role, state))

    state = orchestrator.run(payload.requirement, progress_callback=_on_progress)
    return WorkflowRunResponse(state=state, progress=progress)


@app.get("/workflow/stream")
def stream_workflow(
    requirement: str = Query(min_length=1, max_length=2000),
) -> StreamingResponse:
    if not requirement.strip():
        raise HTTPException(status_code=400, detail="requirement must not be empty")

    events: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def _worker() -> None:
        orchestrator = Orchestrator()

        def _on_progress(role: AgentRole, state: WorkflowState) -> None:
            event = _build_progress_event(role, state)
            events.put(
                {
                    "event": "progress",
                    "data": event.model_dump(mode="json"),
                }
            )

        try:
            state = orchestrator.run(requirement, progress_callback=_on_progress)
            events.put(
                {
                    "event": "completed",
                    "data": state.model_dump(mode="json"),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive API fallback
            events.put({"event": "error", "data": {"detail": str(exc)}})
        finally:
            events.put(None)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    def _event_stream():
        while True:
            item = events.get()
            if item is None:
                break
            yield (
                f"event: {item['event']}\n"
                f"data: {json.dumps(item['data'])}\n\n"
            )

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/ui", response_class=HTMLResponse)
def workflow_ui() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>memoryapp agent console</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; max-width: 900px; }
    input, button { padding: 0.5rem; font-size: 1rem; }
    input { width: 70%; }
    #events, #result { white-space: pre-wrap; background: #f6f8fa; padding: 1rem; border-radius: 6px; }
    #events { min-height: 200px; }
  </style>
</head>
<body>
  <h1>Live Agent Progress</h1>
  <p>Run the full workflow and watch each agent update in real time.</p>
  <input id="requirement" value="Build a memory management app with note search" />
  <button id="runBtn">Run Workflow</button>
  <h2>Progress</h2>
  <div id="events"></div>
  <h2>Final State</h2>
  <div id="result"></div>
  <script>
    const events = document.getElementById('events');
    const result = document.getElementById('result');
    const requirementInput = document.getElementById('requirement');
    const runBtn = document.getElementById('runBtn');
    let source = null;

    function append(line) {
      events.textContent += line + "\\n";
    }

    runBtn.addEventListener('click', () => {
      const requirement = requirementInput.value.trim();
      if (!requirement) {
        append('Requirement is required.');
        return;
      }
      events.textContent = '';
      result.textContent = '';
      if (source) {
        source.close();
      }

      source = new EventSource(`/workflow/stream?requirement=${encodeURIComponent(requirement)}`);
      append(`Starting workflow for: ${requirement}`);

      source.addEventListener('progress', (evt) => {
        const data = JSON.parse(evt.data);
        append(`• ${data.agent} (iteration ${data.iteration}) -> ${data.message_type || 'n/a'} to ${data.recipient || 'n/a'}`);
      });

      source.addEventListener('completed', (evt) => {
        result.textContent = JSON.stringify(JSON.parse(evt.data), null, 2);
        append('Workflow completed.');
        source.close();
      });

      source.addEventListener('error', (evt) => {
        append('Workflow stream error.');
        if (evt?.data) {
          append(evt.data);
        }
        source.close();
      });
    });
  </script>
</body>
</html>"""


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
