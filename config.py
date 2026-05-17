"""
Configuration for the multi-agent system.

Set OPENAI_API_KEY in your environment or .env file to use a real LLM backend.
When OPENAI_API_KEY is not set, the system runs in mock mode using deterministic
prompt-templated responses so it can be used and tested without any API credentials.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# LLM provider settings
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")

# Use mock LLM when no API key is available
USE_MOCK_LLM: bool = not bool(OPENAI_API_KEY)

# Agent behaviour
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
