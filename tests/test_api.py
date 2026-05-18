"""Tests for FastAPI endpoints used to interact with agents."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from api import app

client = TestClient(app)
# Minimum progress count for full workflow run (one event per core agent pass).
MIN_CORE_AGENT_PROGRESS_EVENTS = 4


class TestApi:
    def test_health(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_list_agents(self) -> None:
        response = client.get("/agents")
        assert response.status_code == 200
        roles = {item["role"] for item in response.json()}
        assert roles == {"business_analyst", "architect", "builder", "tester"}

    def test_run_workflow_returns_progress(self) -> None:
        response = client.post(
            "/workflow/run",
            json={"requirement": "Build a memory management app"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["state"]["build_result"] is not None
        assert len(body["progress"]) >= 4
        assert body["progress"][0]["agent"] == "business_analyst"

    def test_run_single_agent(self) -> None:
        response = client.post(
            "/agents/business_analyst/run",
            json={"original_requirement": "Build a memory app"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["requirement_spec"] is not None
        assert body["requirement_spec"]["research_sources"]
        assert body["requirement_spec"]["user_flows"]
        assert body["requirement_spec"]["inputs"]
        assert body["requirement_spec"]["outputs"]
        assert body["requirement_spec"]["color_palette"]
        assert len(body["history"]) == 1

    def test_stream_workflow_returns_events(self) -> None:
        response = client.get(
            "/workflow/stream",
            params={"requirement": "Build a memory management app"},
        )
        assert response.status_code == 200
        chunks = [chunk for chunk in response.text.split("\n\n") if chunk.strip()]
        progress_payloads = []
        completed_payload = None

        for chunk in chunks:
            event_name = None
            data_line = None
            for line in chunk.splitlines():
                if line.startswith("event: "):
                    event_name = line.split("event: ", 1)[1]
                if line.startswith("data: "):
                    data_line = line.split("data: ", 1)[1]
            if event_name == "progress" and data_line:
                progress_payloads.append(json.loads(data_line))
            if event_name == "completed" and data_line:
                completed_payload = json.loads(data_line)

        assert len(progress_payloads) >= MIN_CORE_AGENT_PROGRESS_EVENTS
        assert progress_payloads[0]["agent"] == "business_analyst"
        assert "iteration" in progress_payloads[0]
        assert {
            "business_analyst",
            "architect",
            "builder",
            "tester",
        }.issubset({event["agent"] for event in progress_payloads})
        assert completed_payload is not None
        assert completed_payload["build_result"] is not None

    def test_stream_workflow_rejects_long_requirement(self) -> None:
        response = client.get(
            "/workflow/stream",
            params={"requirement": "x" * 2001},
        )
        assert response.status_code == 422

    def test_ui_page(self) -> None:
        response = client.get("/ui")
        assert response.status_code == 200
        assert "Live Agent Progress" in response.text
