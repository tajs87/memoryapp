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
            WEB RESEARCH:
            - Nielsen Norman Group task-flow guidance suggests each core user goal should follow a clear linear path with a visible success state.
            - WCAG accessibility guidance recommends not relying on color alone and keeping strong contrast for interactive elements and status states.
            - Material-style product guidance favors a limited palette with a primary brand color, neutral surfaces and distinct semantic status colors.

            CLARIFIED REQUIREMENTS:
            - The system shall allow users to manage memory/notes efficiently.
            - Users can create, read, update and delete entries.
            - The system shall support multiple concurrent users.
            - Data must be persisted across sessions.
            - A RESTful API shall be exposed for integrations.

            USER FLOWS:
            - Capture memory: open create form -> enter title, body and tags -> save entry -> show the new memory in the list.
            - Review memory: open the memory list -> search or filter entries -> select one entry -> show the full memory detail view.
            - Update memory: open an existing memory -> edit title, body or tags -> save changes -> confirm the updated state in the detail view.
            - Delete memory: open an existing memory -> confirm delete action -> remove entry -> return to the list without the deleted memory.

            INPUTS:
            - Memory title.
            - Memory body/content.
            - Optional tags or categories.
            - Search query text.
            - User identity/authentication token.

            OUTPUTS:
            - Persisted memory records that can be listed and reopened.
            - Filtered search results for matching memories.
            - Success or error feedback for create, update and delete actions.
            - API responses for integrations.

            COLOR PALETTE:
            - Primary blue: #2563EB.
            - Accent teal: #0D9488.
            - Background slate: #F8FAFC.
            - Surface white: #FFFFFF.
            - Text charcoal: #1F2937.
            - Success green: #16A34A.
            - Error red: #DC2626.

            ASSUMPTIONS:
            - Users are authenticated via JWT tokens.
            - The application targets web and mobile clients.

            OUT OF SCOPE:
            - Payment processing.
            - Third-party social-login.

            FEEDBACK:
            The requirements are broadly sound. Clarify whether offline support
            is needed, whether attachments/media should be supported, and confirm
            the expected daily active user count so the architect can size the
            infrastructure appropriately.
            """
        ),
        "architect": textwrap.dedent(
            """\
            WEB RESEARCH:
            - OWASP authentication guidance recommends short-lived tokens, secure password hashing, and defense-in-depth around login and session flows.
            - Cloud architecture best practices favor stateless application tiers, managed databases, caching, and observable services for horizontal scale.
            - Modern product design guidance recommends mapping end-to-end user journeys, explicit success/error states, and consistent visual styling tokens.

            ARCHITECTURAL REQUIREMENTS:
            - The architecture must support secure authenticated access for multiple concurrent users.
            - The design must persist memory records reliably and expose fast search and retrieval paths.
            - The system must provide clear create, review, update, and delete user journeys across web and mobile-friendly clients.
            - The solution should support accessible styling and consistent interaction feedback.

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

            AUTHENTICATION:
            Use JWT-based authentication with short-lived access tokens, refresh
            tokens stored securely, role-aware authorization checks in the API
            layer, and audit logging for sensitive account actions.

            USER JOURNEYS:
            - New user onboarding: sign in -> land on memory dashboard -> review empty-state guidance -> create first memory.
            - Returning user retrieval: authenticate -> open dashboard -> search or filter memories -> open a selected memory detail view.

            USER FLOWS:
            - Create memory flow: open create screen -> enter title, content and tags -> submit -> validate -> persist record -> show success state.
            - Update memory flow: open memory detail -> edit content -> save changes -> persist revision -> show updated detail state.
            - Delete memory flow: open memory detail -> choose delete -> confirm action -> remove record -> return to filtered list with feedback.

            INPUTS:
            - Authentication credentials or session token.
            - Memory title, content, tags, and optional metadata.
            - Search/filter terms and sort preferences.

            OUTPUTS:
            - Authenticated session state and authorization decisions.
            - Persisted memory records, detail views, and filtered search results.
            - Success, validation, and error feedback across each user journey.

            STYLING:
            - Use a calm blue/teal primary palette with high-contrast text and neutral surfaces.
            - Provide consistent button, form, and status-state styling tokens aligned with the requirement color palette.
            - Ensure error, success, and focus states remain distinguishable without relying on color alone.

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
