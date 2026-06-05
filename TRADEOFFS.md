# Trade-offs

## Built vs. scoped

Built:

- FastAPI backend and chat frontend.
- LangGraph/LangChain agent path when `OPENAI_API_KEY` is configured.
- Offline fallback so the app remains runnable without credentials.
- Persistent SQLite household memory for pantry, equipment, preferences, and allergies.
- Structured local recipe catalog with deterministic pantry/equipment fit checks.
- External food search tool with authoritative fallback links.
- User-friendly progress text and engineer trace mode.
- Policy handling for off-topic, medical/dietary advice, food safety, and allergen notices.
- Docker setup and tests for the highest-risk deterministic behavior.

Scoped but simplified:

- External recipe ingestion is not fully implemented. The architecture supports structured catalog entries, but the demo does not crawl/parse arbitrary web recipes into the schema.
- Streaming token output is represented as immediate progress states plus final responses. Full token streaming would be the next UI/API iteration.
- Memory controls are functional but not production-grade. Consent, deletion, retention, and sensitive-data classification need a real product/legal pass.

## Specific trade-offs

- I used a small local catalog rather than broad recipe retrieval. This makes the core incident class testable: PantryPal must not suggest impossible recipes when equipment is missing.
- I kept the frontend vanilla and served by FastAPI. That reduced build-chain risk and left more time for backend judgment, tools, and guardrails.
- I included an offline fallback. The assessment requires LangGraph and LangChain, which are present in the real path, but reviewers without an API key can still exercise the product behavior.
- I enforced allergen notice behavior in backend policy rather than relying only on the model. This can feel repetitive, but legal consistency beats conversational elegance.
- I classified medical and food-safety requests with simple deterministic helpers. A production version should add eval-backed model classification and human-reviewed policy examples.

## What I would do next

- Add real streaming responses and structured progress events.
- Add prompt/tool evals for the incident cases, medical refusals, food safety refusals, and allergen notice consistency.
- Build approved recipe ingestion with data-rights constraints and schema validation.
- Add account-level memory consent, deletion, and retention controls.
- Add model routing and token/cost telemetry.
- Add CI/CD, staging deploys, rollback, and on-call runbooks.
- Expand the recipe/equipment taxonomy using support interview data.

## Known issues and unhandled cases

- The local recipe catalog is intentionally small, so breadth is limited.
- Offline fallback is deterministic and less flexible than a real LLM agent.
- External search depends on network availability; fallback links keep food-safety redirects usable when search fails.
- Allergy storage exists for prototype UX, but production needs legal-approved consent and deletion flows.
- The app uses a single demo user rather than authentication or multi-tenant isolation.
