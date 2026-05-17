"""Tests for FastAPI endpoints used to interact with agents."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


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
        assert len(body["history"]) == 1

    def test_stream_workflow_returns_events(self) -> None:
        response = client.get(
            "/workflow/stream",
            params={"requirement": "Build a memory management app"},
        )
        assert response.status_code == 200
        assert "event: progress" in response.text
        assert "event: completed" in response.text

    def test_ui_page(self) -> None:
        response = client.get("/ui")
        assert response.status_code == 200
        assert "Live Agent Progress" in response.text
