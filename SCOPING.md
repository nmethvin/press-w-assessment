# PantryPal V1 Scoping

## Scope committed

- Build a household-focused, food-adjacent cooking assistant: cooking questions, recipe suggestions, ingredient substitutions, pantry-aware meal ideas, cookware/equipment-aware feasibility checks, wine pairings, and menu/hosting ideas.
- Make pantry and equipment first-class persistent profile data. The assistant should remember available ingredients and cookware across sessions, ask follow-up questions when constraints are missing or ambiguous, and avoid recommending recipes that require missing equipment without offering a workaround or similar alternative.
- Demonstrate LLM-driven tool use through a LangGraph agent that can decide when to search recipes, check pantry/equipment fit, update/read user profile data, suggest substitutions, and call an external search tool for authoritative or fresh information.
- Include safety guardrails for off-topic, food safety, allergy, and medical/dietary-advice cases. Recipe or ingredient suggestions must include an allergen notice via model instruction and backend/UI enforcement.
- Ship a clean chat UI with two visibility modes: user-friendly progress/tool status for normal users and an engineer/debug mode with fuller tool traces.

## Scope cut

- Restaurant recommendations are out of demo scope. They are food-adjacent, but they introduce location, reviews, freshness, monetization, and trust questions that are separate from the household cooking moment.
- Voice and hands-free cooking are out of v1 implementation scope. The architecture should not block future voice, but building it now would dilute the core pantry/equipment reliability problem.
- Favorites, grocery export, meal-plan shopping lists, and family cookbook/PDF ingestion are deferred. They are real user needs, but the first reliability gap is whether PantryPal can suggest feasible things to cook with what a user actually has.
- Full production memory for allergies, health mentions, and personal data is not included. The prototype may let users provide preferences and allergies in session/profile context, but production storage needs consent, classification, deletion, and retention policy before launch.

## Contradictions resolved

- Priya wants "cooking only"; Marcus wants broad food-adjacent scope. Decision: food-adjacent but household-bounded. PantryPal can help with cooking, ingredients, meal planning, substitutions, hosting menus, and pairings, but not restaurant discovery or unrelated tasks.
- Priya wants responses under two seconds; Marcus prefers quality over speed. Decision: provide visible feedback within two seconds and stream/progress tool activity, but do not promise complete multi-tool answers in under two seconds.
- Marcus wants health-adjacent usefulness; Diane says no medical or therapeutic advice. Decision: support neutral user preferences like vegetarian, keto, spicy, or nut-free as constraints, but refuse claims about what is medically appropriate for diabetes, pregnancy, weight loss, or other health conditions.
- Product wants personality; the recent incident shows prompt changes weakened constraint checking. Decision: personality belongs in the response layer, while feasibility checks must be deterministic tool behavior with tests and review.

## What I'd reject

- I would reject a prompt-only equipment checker. The recent production incident is evidence that important constraints can fall out of the prompt or context window. Equipment and pantry fit need structured data and deterministic checks.
- I would reject dumping all chat history into "memory." It is expensive, hard to delete, legally risky, and unreliable for constraints that users expect the product to honor.
- I would reject routing every query through a GPT-4-class model. The board's cost target requires model routing, caching, deterministic tools, and measurement from the beginning.
- I would reject medical nutrition advice framed as recipe help. The product can filter against stated preferences, but it cannot say a recipe is appropriate for a medical condition.
- I would reject unreviewed production prompt changes. Prompt and tool-policy changes need evals, code review, and rollback discipline like any other production behavior.

## Clarifying questions

- What is the exact consent and deletion experience required before PantryPal stores dietary preferences, allergies, or health-adjacent data?
- What allergen notice language has legal approved, and can it live as a persistent UI element plus response-level fallback?
- What model providers and cost ceilings are already contracted or preferred?
- What recipe data rights do we have, and can externally discovered recipes be stored, summarized, or only linked?
- What age-gating or under-13 policy should launch with the product?

## Assumptions made

- The demo can use a small local structured recipe catalog and persist user pantry/equipment/profile data locally, while documenting the production path.
- "Keto" is treated as a user preference, not a medical claim, unless the user ties it to a health condition.
- Food safety questions can receive general safe-handling guidance and links to authoritative sources, but not a specific determination that a user's food is safe to eat.
- The frontend can show tool progress without exposing raw internal debug traces unless engineer mode is enabled.
- For the prototype, external recipe discovery can demonstrate ingestion into a structured schema without guaranteeing production data rights.

## Risks accepted

- Persistent profile memory in the prototype is intentionally narrower than Marcus's full relationship vision. This accepts some product incompleteness to avoid unsafe storage of sensitive data.
- The local recipe catalog will be small, so breadth will be limited. This is acceptable because the demo is proving architecture and constraint correctness rather than recipe coverage.
- External search quality and availability may vary. The core cooking flow should still work against the local catalog.
- Allergen notices may feel slightly repetitive. Legal consistency is more important than conversational elegance for launch.
- The 200k MAU path requires operational work beyond the prototype: CI/CD, observability, evals, prompt governance, on-call, and cost controls.
