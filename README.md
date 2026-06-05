# Director of Engineering Assessment - Build Day

**Role:** Director of Engineering
**Time:** 4 hours, self-timeboxed
**Submission:** Public GitHub repo, or private repo shared with @elmdecoste and @bgreal5

---

## Before you start

Your 4-hour window starts now. The delivery system tracks the clock automatically, so there's no need to mark a start time yourself.

You've already read the PantryPal brief. Now it's time to make decisions and ship.

How to work:

1. Decide what to build, what to plan, and what to communicate.
2. Commit as you go so we can see your progress.
3. At the 4-hour mark, stop. If you commit past that point, note them as post-window in your writeup. We'd rather see honesty than a silent overrun.

If something goes wrong (life, illness, internet), just tell us. Rescheduling is fine; silent extensions are not.

---

## Deliverables

You will submit six things:

### 1. A scoping document (`SCOPING.md`)

Before writing code, produce a short scoping doc with the following sections:

- **Scope committed:** what you're actually building, as a tight list
- **Scope cut:** what you heard but decided not to do, with reasoning
- **Contradictions resolved:** where stakeholders disagreed, and how you decided
- **What I'd reject:** one or more things a reasonable engineer might build here that you think are actively wrong, and why
- **Clarifying questions:** what you'd want answered before a production build
- **Assumptions made:** what you decided without asking
- **Risks accepted:** what could bite later and why you're accepting it

Keep this to 1-2 pages. Three sharp, defensible entries per section beats fifteen generic ones.

### 2. A stakeholder alignment email (`STAKEHOLDER_EMAIL.md`)

You've read the inputs from Priya, Marcus, Jordan, and Diane. They don't fully agree. Write the email you'd actually send to align them before you start building. This isn't a summary of what you found. It's a proposal for how to move forward, addressed to real people with real opinions. This is an email, not a memo. Keep it to something people would actually read.

### 3. A technical strategy (`TECHNICAL_STRATEGY.md`)

PantryPal is at 12k MAU. The board expects 200k by Q4. Write the technical strategy for getting there. This should cover:

- How you'd decompose the work across the existing team
- What you'd sequence first and why
- How you'd handle the scaling, cost, and operational challenges between here and there

This is not a feature roadmap. It's a technical leadership document about how you'd get a real product to real scale with the team and constraints you've been given. Keep it to 2-3 pages. Specific and opinionated beats comprehensive and safe.

### 4. A working system

Build a working prototype that demonstrates your technical vision for the product. Baseline requirements (non-negotiable):

- A Python backend using **FastAPI** and **LangGraph**
- LLM-driven tool use: the model decides when to invoke tools (no hardcoded sequences)
- At least one external tool (web search or equivalent)
- All LLM calls routed through **LangChain** (no model-specific SDKs directly)
- A chat frontend (stack of your choice; we recommend something you're fast in)
- Docker setup, so we can clone and run

Everything else is up to you. Implement what your scope says you'll implement.

### 5. A README

Setup instructions, example requests (curl is fine), and anything a teammate would need to run and understand the code.

### 6. A trade-offs writeup (`TRADEOFFS.md`)

Short doc covering:

- What you actually built vs. what you scoped (time pressure is expected; tell us what got cut)
- Specific trade-offs you made and why
- What you'd do next with more time
- Known issues or unhandled cases

---

## Expectations and norms

- **Use AI tools.** We do, and we expect you to. We're evaluating your judgment and your output, not whether you can type fast.
- **Don't optimize for feature count.** A smaller working system with defensible choices beats a larger system built on unexamined assumptions.
- **Ship something that runs.** If you have to cut, cut scope before quality.
- **Document unfinished work.** Stubs with clear TODOs are fine. Leave a clear trail of what's unfinished.
- **Expect robustness to be tested.** We'll exercise your system with inputs you didn't design for.
- **How you allocate your time matters.** A DoE who spends 3.5 hours coding and 15 minutes on strategy is telling us something. So is one who writes a beautiful strategy doc and ships nothing.

Good luck.
