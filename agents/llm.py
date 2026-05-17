"""
LLM abstraction layer.

Provides a unified interface that works with a real OpenAI-compatible backend
or a built-in mock backend when no API key is configured.
"""

import textwrap
from abc import ABC, abstractmethod
from typing import List

import config


class BaseLLM(ABC):
    """Common interface for all LLM backends."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return an LLM completion as a plain string."""


class OpenAILLM(BaseLLM):
    """OpenAI (or compatible) backend."""

    def __init__(self) -> None:
        from openai import OpenAI  # imported lazily so mock mode needs no install

        self._client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )
        self._model = config.LLM_MODEL

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""


class MockLLM(BaseLLM):
    """
    Deterministic mock backend used when no API key is provided.

    Each agent passes a distinctive keyword in its system prompt so that
    the mock can return an appropriate template response.
    """

    _RESPONSES: dict = {
        "business_analyst": textwrap.dedent(
            """\
            CLARIFIED REQUIREMENTS:
            - The system shall allow users to manage memory/notes efficiently.
            - Users can create, read, update and delete entries.
            - The system shall support multiple concurrent users.
            - Data must be persisted across sessions.
            - A RESTful API shall be exposed for integrations.

            ASSUMPTIONS:
            - Users are authenticated via JWT tokens.
            - The application targets web and mobile clients.

            OUT OF SCOPE:
            - Payment processing.
            - Third-party social-login.

            FEEDBACK:
            The requirements are broadly sound. Clarify whether offline support
            is needed and confirm the expected daily active user count so the
            architect can size the infrastructure appropriately.
            """
        ),
        "architect": textwrap.dedent(
            """\
            SYSTEM OVERVIEW:
            A three-tier web application with a stateless REST API, a relational
            database for persistence and a caching layer for read-heavy workloads.

            COMPONENTS:
            - API Gateway: routes requests, handles rate-limiting and auth.
            - Application Service (Python/FastAPI): business logic layer.
            - PostgreSQL: primary relational data store.
            - Redis: caching and session storage.
            - Object Storage (S3-compatible): binary assets.

            TECHNOLOGY STACK:
            Python 3.12, FastAPI, PostgreSQL 16, Redis 7, Docker, Kubernetes

            SCALABILITY:
            Horizontal pod autoscaling on the application tier; read replicas for
            the database; Redis cluster mode for cache scalability.

            PERFORMANCE:
            Target p99 latency <200 ms; CDN for static assets; async I/O
            throughout the application layer.

            DEPLOYMENT:
            Kubernetes on a managed cloud provider (EKS/GKE/AKS); CI/CD via
            GitHub Actions; blue-green deployments for zero-downtime releases.
            """
        ),
        "builder": textwrap.dedent(
            """\
            BUILD STATUS: SUCCESS

            ARTIFACTS:
            - memoryapp-api:latest (Docker image)
            - memoryapp-migrations:latest (Docker image)
            - helm/memoryapp-1.0.0.tgz (Helm chart)

            DEPLOYMENT URL: https://memoryapp.example.com

            LOGS:
            [INFO]  Dependencies installed successfully.
            [INFO]  Unit tests passed (47/47).
            [INFO]  Docker images built and pushed to registry.
            [INFO]  Helm chart deployed to staging cluster.
            [INFO]  Health check passed – all pods Running.
            """
        ),
        "tester": textwrap.dedent(
            """\
            TEST SUMMARY:
            Tests run   : 52
            Tests passed: 50
            Tests failed: 2

            FAILURES:
            - test_concurrent_write: race condition under high load (>500 rps).
            - test_search_unicode: special characters not handled in search index.

            COVERAGE: 87%

            ITERATION NEEDED: Yes
            SUGGESTED AGENT: architect
            ITERATION REASON:
            The concurrent write failure indicates a missing optimistic-locking
            strategy. The architect should revisit the database access patterns
            and add explicit locking guidance before the builder re-implements
            the affected module.
            """
        ),
    }

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        lower = system_prompt.lower()
        for keyword, response in self._RESPONSES.items():
            if f"[agent:{keyword}]" in lower:
                return response
        return (
            "Mock LLM: no matching template found for the provided system prompt. "
            "Ensure the system prompt contains one of: "
            + ", ".join(f'"[AGENT:{k.upper()}]"' for k in self._RESPONSES)
        )


def get_llm() -> BaseLLM:
    """Return the appropriate LLM backend based on configuration."""
    if config.USE_MOCK_LLM:
        return MockLLM()
    return OpenAILLM()
