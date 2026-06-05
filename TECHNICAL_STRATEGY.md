# Technical Strategy: PantryPal From 12k to 200k MAU

## Direction

PantryPal should scale around a simple principle: the assistant can have personality, but product-critical constraints must be structured, testable, and observable. At 12k MAU, prompt-only behavior can survive by luck and manual fixes. At 200k MAU, it will fail in expensive and visible ways.

The core technical strategy is to separate conversation from decision support:

- Conversation layer: tone, follow-up questions, streaming, and natural chat.
- Tool layer: recipe retrieval, pantry/equipment checks, substitutions, profile reads/writes, safety redirects, and external search.
- Policy layer: allergen notices, off-topic boundaries, medical/dietary refusal, food safety refusal, and memory rules.
- Operations layer: evals, monitoring, incident response, CI/CD, prompt review, and cost telemetry.

The product should feel like a friend who cooks, but the engineering system should behave like a reliable decision engine.

## Work decomposition

### Platform squad

Raj should lead the profile, API, and production-readiness track, with Sofia owning durable pieces and Alex paired deliberately so knowledge does not stay concentrated. This squad should own:

- User profile APIs for pantry, equipment, preferences, and explicit memory controls.
- Persistence model for household constraints, with a path to consent/deletion for sensitive categories.
- Request tracing, structured logs, token/tool-call metrics, and latency dashboards.
- CI/CD hardening, staging parity, production deploy automation, and rollback.
- On-call rotation and incident runbooks.

This track is also a retention risk mitigation move. Raj holds too much platform knowledge; giving him a visible, important charter while spreading ownership is the right first move.

### Product squad

Maya should lead the chat and profile UX. Chris can move fast on full-stack integration but needs tight scope boundaries; Nia should take well-contained UI states under Maya's mentorship. This squad should own:

- Chat UI with streaming/progress states.
- Household profile setup and editing for ingredients and equipment.
- User-friendly tool-status display and an engineer/debug mode.
- Graceful workaround UX when a recipe does not fit.
- Later: favorites, grocery export, meal planning flows, and voice UI exploration.

The UI does not need a permanent design system for V1, but it needs to feel coherent and trustworthy. The main product sin to avoid is a polished chat surface that still suggests impossible recipes.

### AI/ML squad

Sam should lead the LangGraph/tool orchestration work, but the process has to change immediately. Prompt and agent changes need review, evals, versioning, and rollback. Lena should own a meaningful slice of evals/model-routing to reduce over-dependence on Sam; Tyler should work on fixtures and regression cases with close review. This squad should own:

- LangGraph agent design and LangChain model integration.
- Tool schema design for profile lookup, recipe search, fit checks, substitutions, and external search.
- Prompt and policy versioning.
- Automated evals for equipment constraints, pantry constraints, medical advice refusal, food safety refusal, off-topic routing, and allergen notices.
- Model routing and cost experiments.

Sam's adjacent recipe project needs to be addressed directly as an IP/conflict concern, not whispered about. Separately, his fast-but-loose merge process has to end. At 200k MAU, unreviewed prompt changes are production changes with real user and legal impact.

### Data

James should own the recipe and constraint data track, with a path into ML-adjacent work through retrieval quality, schema design, and eval datasets. This track should include:

- Recipe schema with required equipment, ingredients, time, servings, cuisine, dietary tags, and substitution affordances.
- Equipment taxonomy that maps user language to structured constraints.
- Recipe ingestion pipeline for approved sources.
- Data quality checks for missing equipment and unsafe tags.
- Analytics on failed recipe fits and workaround acceptance.

## Sequencing

### Phase 1: Stabilize the core loop

The first sequence is not growth work; it is trust work.

- Move pantry/equipment constraints out of the prompt and into structured profile data.
- Build deterministic recipe-fit checks.
- Add evals for the exact incident class: no oven means no oven recipes unless a valid workaround is offered.
- Add prompt/tool review and rollback discipline.
- Add observability for tool calls, model cost, latency, refusals, and constraint failures.

This comes first because growth will amplify every reliability flaw. If the assistant ignores cookware constraints at 12k MAU, paid acquisition only buys more churn.

### Phase 2: Ship V1 assistant architecture

Once the core loop is testable, ship the household cooking assistant:

- LangGraph agent with model-decided tool use.
- Local structured recipe catalog plus ingestion path for externally discovered recipes.
- Persistent household memory for ingredients and equipment.
- Session/profile support for preferences and allergies, with legal-approved disclosure behavior.
- External search for authoritative food-safety/general cooking references.
- Clean chat UI with visible progress within two seconds.

This phase should prove the technical vision without pretending that every future feature is complete.

### Phase 3: Cost and scale hardening

Before marketing drives Q3 volume, build the cost and reliability envelope:

- Route simple classification and common cooking Q&A to cheaper/faster models.
- Reserve stronger models for multi-step planning and ambiguous requests.
- Cache common substitutions, cooking facts, and safe redirects.
- Keep deterministic checks outside the LLM.
- Track blended cost per query, p95 latency, tool failure rate, and answer quality evals.
- Load test the API and agent paths against expected Q4 traffic.

The board's under-$0.01/query target is achievable only if the system is designed to spend LLM tokens where they create user value.

### Phase 4: Expand retention features

After the assistant reliably respects constraints, add the features Jordan is hearing in interviews:

- Favorites and saved recipes.
- Grocery list export.
- Meal planning.
- Richer long-term preference memory with consent/deletion controls.
- Cookbook import if data rights and ingestion quality can be solved.
- Voice/hands-free cooking mode.

These are likely important for retention, but they should not outrun the trust foundation.

## Scaling, cost, and operations

### Scaling

The API should be stateless where possible, with durable profile and recipe data behind it. Agent runs should carry trace IDs across frontend, backend, model calls, and tools. Recipe fit checks should be deterministic functions over structured data, not emergent model behavior.

At 200k MAU, the system needs clear separation between synchronous chat paths and slower enrichment paths. External recipe ingestion, catalog enrichment, and analytics should be background jobs. User chat should not block on ingestion unless explicitly requested and safely bounded.

### Cost

Cost control should be designed into the agent:

- Model routing by task complexity.
- Token budgets and max tool-call limits.
- Cached answers for common questions.
- Local recipe retrieval before web search.
- Deterministic validation instead of model re-asking.
- Per-query cost telemetry visible to engineering and product.

The target metric should be blended cost per successful user task, not just raw model cost per call. A cheap answer that suggests an impossible recipe is still expensive.

### Reliability

The recent incident points to three missing systems: change control, evals, and monitoring.

Every prompt, tool, recipe schema, and safety policy change should go through review. The team needs regression evals that include known bad cases from support. Production should emit structured events when the assistant suggests a recipe, checks fit, finds missing equipment, offers a workaround, refuses medical advice, or appends an allergen notice.

On-call needs to move from "whoever notices" to a rotation with alert ownership. Incidents should have timestamps, severity, impact, root cause, action items, and follow-up accountability.

### Legal and privacy

Legal constraints should be implemented as product behavior, not just prompt text:

- Allergen notices enforced by backend/UI when recipes or ingredients are suggested.
- Medical/dietary advice refusal policy.
- Food safety refusal policy with authoritative-source redirect.
- Sensitive memory classification before storing allergies, health mentions, or personal details.
- Deletion and retention story before production launch.
- COPPA stance before opening the product to under-13 users.

## Leadership priorities

The first engineering leadership move is to create clarity without slowing the team to a crawl. That means:

- Give each squad a clear owner and crisp charter.
- Reduce single-person dependencies on Raj and Sam.
- Address Sam's adjacent project and unreviewed AI deploys directly.
- Promote review and evals as quality accelerators, not bureaucracy.
- Use Jordan's support data as an input to engineering tests.
- Make cost, latency, reliability, and constraint correctness visible weekly.

The path to 200k MAU is not a bigger chatbot. It is a cooking assistant that remembers the right things, refuses the right things, uses tools deliberately, and earns trust every time it says "make this instead."
