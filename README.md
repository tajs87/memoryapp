# memoryapp – Multi-Agent System

A four-agent pipeline that takes a raw software requirement from idea to tested
deployment, with automatic iteration when tests reveal issues.

## Agents

| # | Agent | Responsibility |
|---|-------|---------------|
| 1 | **Business Analyst** | Clarifies requirements, lists assumptions, flags out-of-scope items, provides feedback |
| 2 | **Architect** | Designs the system architecture with scalability and performance considerations |
| 3 | **Builder** | Builds and deploys the application, produces artifacts and a deployment URL |
| 4 | **Tester** | Validates the build against requirements; if failures are found, triggers an iteration back to the appropriate agent |

The **Orchestrator** coordinates all four agents.  When the Tester requests an
iteration the pipeline restarts from the suggested agent (e.g. Architect →
Builder → Tester) and repeats up to `MAX_ITERATIONS` times.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) set your OpenAI API key – omit to run in mock mode
export OPENAI_API_KEY=sk-...

# 3. Run with an inline requirement
python main.py "Build a memory management app with note search"

# 4. Or run interactively
python main.py
```

## Configuration

All settings can be overridden via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(empty)* | OpenAI key; unset → mock mode |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Compatible with any OpenAI-API endpoint |
| `LLM_MODEL` | `gpt-4o` | Model name |
| `MAX_ITERATIONS` | `3` | Maximum tester→agent feedback cycles |

## Project layout

```
memoryapp/
├── agents/
│   ├── business_analyst.py   # Agent 1 – Business Analyst
│   ├── architect.py          # Agent 2 – Architect
│   ├── builder.py            # Agent 3 – Builder / Deploy
│   ├── tester.py             # Agent 4 – Tester / QA
│   ├── base_agent.py         # Shared abstract base
│   ├── llm.py                # LLM abstraction (OpenAI + Mock)
│   └── parser.py             # Shared section-parser utility
├── models/
│   └── __init__.py           # Pydantic models (WorkflowState, etc.)
├── tests/
│   ├── test_business_analyst.py
│   ├── test_architect.py
│   ├── test_builder.py
│   ├── test_tester.py
│   └── test_orchestrator.py
├── orchestrator.py           # Multi-agent coordinator
├── main.py                   # CLI entry point
├── config.py                 # Configuration
└── requirements.txt
```

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```
