# PantryPal Assessment Demo

PantryPal is a household-focused cooking assistant prototype. It demonstrates the assessment strategy in code: persistent pantry/equipment memory, deterministic recipe-fit checks, LangGraph tool orchestration, external search, and legal/safety guardrails.

The app is intentionally compact. FastAPI serves both the API and a vanilla chat frontend so reviewers can clone, run, and test the core behavior quickly.

## What is built

- Python backend using FastAPI.
- LangGraph agent with LangChain tools.
- LLM calls routed through LangChain via `langchain-openai` when `OPENAI_API_KEY` is set.
- Offline fallback mode so the demo still runs without an LLM key.
- Persistent SQLite household memory for pantry, equipment, preferences, and allergies.
- Structured local recipe catalog with required equipment and ingredients.
- Deterministic fit checks before recommending catalog recipes.
- External search tool using DuckDuckGo Search, with authoritative food-safety fallback links.
- Chat frontend with profile editing, user-friendly tool status, and engineer trace mode.
- Docker setup.

## Run locally

```bash
cd /Users/nathanmethvin/Documents/projects/press-w-assessment
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

With an OpenAI key:

```bash
export OPENAI_API_KEY=your-key
export PANTRYPAL_FAST_MODEL=gpt-4o-mini
export PANTRYPAL_SMART_MODEL=gpt-4o
PYTHONPATH=backend uvicorn app.main:app --reload
```

Without a key, the app uses an offline deterministic fallback. That fallback is not a replacement for the LangGraph production path, but it keeps the prototype reviewable.

## Run with Docker

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

To run the LangGraph/OpenAI path in Docker:

```bash
OPENAI_API_KEY=your-key docker compose up --build
```

## Model routing

PantryPal uses a small router before invoking the agent:

- `PANTRYPAL_FAST_MODEL`, default `gpt-4o-mini`, handles ordinary household cooking questions.
- `PANTRYPAL_SMART_MODEL`, default `gpt-4o`, handles complex planning, dinner-party/menu, wine-pairing, and longer multi-constraint requests.
- Off-topic, medical, and food-safety policy responses bypass the LLM where deterministic handling is safer and cheaper.

The chat response includes `model`, `model_tier`, and `routing_reason`, and the UI status line shows the selected tier.

## Example requests

Health check:

```bash
curl http://localhost:8000/api/health
```

Get the demo profile:

```bash
curl http://localhost:8000/api/profile/demo
```

Update household memory:

```bash
curl -X PUT http://localhost:8000/api/profile/demo \
  -H "Content-Type: application/json" \
  -d '{
    "pantry": ["chicken", "lemon", "garlic", "olive oil", "herbs"],
    "equipment": ["stovetop", "pan", "knife"],
    "preferences": ["fast", "stovetop"],
    "allergies": []
  }'
```

Ask for a recipe that would normally need an oven:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","message":"I want roasted chicken tonight"}'
```

Ask a food-safety question:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","message":"Is this chicken safe to eat after sitting out?"}'
```

Ask an off-topic question:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","message":"Write my cover letter"}'
```

## Architecture

Important files:

- `backend/app/main.py`: FastAPI app, static frontend, chat/profile endpoints.
- `backend/app/agent/graph.py`: LangGraph agent setup, policy handling, offline fallback.
- `backend/app/agent/tools.py`: LangChain tools exposed to the agent.
- `backend/app/domain/recipes.py`: recipe schema, search, deterministic fit checks.
- `backend/app/domain/policy.py`: off-topic, medical, food-safety, and allergen policy helpers.
- `backend/app/storage.py`: SQLite persistence and seed catalog.
- `backend/app/static/`: chat frontend.

## Tests

```bash
PYTHONPATH=backend pytest backend/tests
```

## Assessment docs

- `SCOPING.md`
- `STAKEHOLDER_EMAIL.md`
- `TECHNICAL_STRATEGY.md`
- `IMPLEMENTATION_PLAN.md`
- `TRADEOFFS.md`
