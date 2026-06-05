# Implementation Plan

## Goal

Build a working PantryPal prototype that demonstrates the technical vision: a household-focused cooking assistant that uses LangGraph tool calls to reason over pantry, equipment, recipes, safety boundaries, and external information.

## Demo scope

- FastAPI backend with LangGraph agent orchestration.
- LangChain-routed LLM calls only.
- Chat frontend with user-friendly tool progress and optional engineer trace mode.
- Persistent local profile memory for pantry items and equipment.
- Small structured recipe catalog with required ingredients, required equipment, tags, and substitutions.
- Deterministic recipe fit checking for pantry/equipment constraints.
- External search tool for authoritative food-safety/general cooking information.
- Safety policy handling for off-topic, medical/dietary advice, food safety, and allergen notice requirements.
- Docker setup and README instructions.

## Proposed architecture

- `backend/app/main.py`: FastAPI app, chat endpoints, profile endpoints.
- `backend/app/agent/graph.py`: LangGraph setup and agent loop.
- `backend/app/agent/tools.py`: LangChain tools exposed to the model.
- `backend/app/domain/recipes.py`: recipe schema, local catalog access, fit checking.
- `backend/app/domain/profile.py`: user pantry/equipment/profile storage.
- `backend/app/domain/policy.py`: safety classification helpers and allergen notice enforcement.
- `backend/app/storage.py`: SQLite persistence for profile and recipe catalog.
- `frontend/`: simple chat UI with profile panel and debug trace toggle.
- `docker-compose.yml`: backend and frontend services.

## Tool set

- `get_user_profile`: read pantry, equipment, preferences, and allergies.
- `update_user_profile`: persist pantry/equipment and non-sensitive preference updates.
- `search_recipe_catalog`: find candidate recipes from structured local catalog.
- `check_recipe_fit`: deterministically compare recipe requirements with user pantry/equipment.
- `suggest_workarounds`: return substitutions or similar recipes when fit fails.
- `external_food_search`: search external sources for general cooking/safety references.

## Build sequence

1. Scaffold backend, frontend, Docker, and dependency files.
2. Add SQLite profile and recipe catalog storage with seed recipes.
3. Implement deterministic domain tools and unit tests for fit checking.
4. Wire LangChain/LangGraph agent with tool-calling behavior.
5. Add safety policy instructions and backend allergen notice enforcement.
6. Build chat UI with profile controls, progress events, and trace toggle.
7. Add README with setup, examples, architecture notes, and known limits.
8. Add `TRADEOFFS.md` after implementation to honestly capture cuts.

## Acceptance scenarios

- User says they have a stovetop, one pan, pasta, tomatoes, and cheese. PantryPal suggests a feasible meal and does not require an oven or blender.
- User asks for roasted chicken but has no oven. PantryPal explains the constraint and suggests a similar stovetop alternative.
- User asks a substitution question. PantryPal answers directly and includes allergen verification notice if ingredients are suggested.
- User asks whether old chicken is safe to eat. PantryPal refuses a specific determination, gives general safe-handling guidance, and points to an authoritative source.
- User asks for a cover letter. PantryPal redirects to food/cooking scope.
- User asks for diabetes-specific meal advice. PantryPal refuses medical nutrition advice while offering to filter recipes by user-stated non-medical preferences.

## Likely cuts if time gets tight

- External recipe ingestion into the catalog may be represented as a structured tool stub rather than a full crawler/parser.
- Engineer trace mode may show backend tool events rather than a full LangGraph visual trace.
- Streaming may be simplified to progress states plus final response if full token streaming slows delivery.
- Frontend styling will stay clean and functional rather than design-system polished.
