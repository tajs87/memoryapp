# memoryapp – Multi-Agent System

A four-agent pipeline that takes a raw software requirement from idea to tested
deployment, with automatic iteration when tests reveal issues.

## Agents

| # | Agent | Responsibility |
|---|-------|---------------|
| 1 | **Business Analyst** | Clarifies requirements, references relevant public best practices, defines user flows with inputs/outputs, proposes colors, and flags assumptions/out-of-scope items |
| 2 | **Architect** | Designs the system architecture using public best practices, including authentication, journeys/flows, styling, scalability, and performance considerations |
| 3 | **Builder** | Builds the application from business and architecture outputs, deploys it in containers, tracks requirement coverage and unit/regression tests, and reports testable URLs |
| 4 | **Tester** | Validates the build against business and architecture requirements; if failures are found, routes iteration back to the appropriate agent |

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

## API mode (interact with each agent + progress tracking)

```bash
# Run API locally
uvicorn api:app --host 0.0.0.0 --port 8000
```

- `GET /agents` → list all available agents and responsibilities.
- `POST /agents/{agent_role}/run` → run a single agent with a provided
  `WorkflowState` payload (lets you interact with each agent directly).
- `POST /workflow/run` → run the full multi-agent flow.  
  Response contains:
  - `state`: final workflow state
  - `progress`: ordered per-agent progress events (agent, iteration, message type,
    recipient, message count)
- `GET /workflow/stream?requirement=...` → stream live per-agent progress events
  (SSE) and a final `completed` event with final state.
- `GET /ui` → browser console to start a workflow, watch live agent progress, and
  inspect final state.

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
├── api.py                    # FastAPI entry point (agent interaction + progress)
├── config.py                 # Configuration
└── requirements.txt
```

## How to deploy

### Option A: local container deployment (fastest)

```bash
docker build -t memoryapp:latest .
docker run --rm -p 8000:8000 -e MAX_ITERATIONS=3 memoryapp:latest
```

Then open:
- `http://localhost:8000/health`
- `http://localhost:8000/ui`

### Option B: Azure Container Apps

1. Create and push the image:

```bash
docker build -t <ACR_NAME>.azurecr.io/memoryapp:latest .
az acr login --name <ACR_NAME>
docker push <ACR_NAME>.azurecr.io/memoryapp:latest
```

2. Deploy API to Azure Container Apps:

```bash
az containerapp create \
  --name memoryapp-agents \
  --resource-group <RESOURCE_GROUP> \
  --environment <ACA_ENVIRONMENT> \
  --image <ACR_NAME>.azurecr.io/memoryapp:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server <ACR_NAME>.azurecr.io \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars MAX_ITERATIONS=3
```

3. Verify deployment:

```bash
curl https://<APP_URL>/health
curl https://<APP_URL>/agents
curl -X POST https://<APP_URL>/workflow/run \
  -H "Content-Type: application/json" \
  -d '{"requirement":"Build a memory management app with note search"}'
```

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```
