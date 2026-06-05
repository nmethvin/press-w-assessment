```
From: Dana Levitt (outgoing Director of Engineering)
To: [You]
Subject: Handoff notes - the team
Date: Last Thursday
```

Hey - congrats on the role. Sorry I can't overlap with you in person but wanted to leave you something useful. Here's where the team stands as of my last day.

We're at 11 engineers across three squads. Org chart is technically flat under the DoE (you) but each squad has a de facto lead.

---

**Platform Squad** (infra, APIs, data layer)

- **Raj Patel** - Senior Backend Engineer, ~2 years. Strongest systems thinker on the team. Owns the API layer and our deployment pipeline (such as it is). I'll be honest: I think Raj is looking around. He hasn't said anything directly but he's been less engaged the last couple months and took a couple "doctor's appointments" that felt like interviews. I didn't address it because I was already on my way out. If you lose Raj you lose a lot of institutional knowledge about the platform.

- **Sofia Torres** - Backend Engineer, ~1 year. Solid, reliable, doesn't need hand-holding. Good at grinding through the unsexy work. Probably under-leveled for what she's doing.

- **Alex Kim** - Junior Backend Engineer, 6 months. Learning fast. Raj has been mentoring him but if Raj leaves, Alex is going to need support.

**Product Squad** (frontend, UX, product-facing features)

- **Maya Washington** - Frontend Lead, 1.5 years. Best product instincts on the team. Good at translating Priya's requirements into something buildable. She'll be your best ally for shipping user-facing work.

- **Chris O'Brien** - Full-Stack Engineer, ~1 year. Capable but has a tendency to over-engineer things. Built our current chat UI. Sometimes needs to be pulled back to scope.

- **Nia Okafor** - Junior Frontend, 4 months. Still ramping. Maya's been mentoring her. Shows promise but isn't independent yet.

**AI/ML Squad** (model integration, inference pipeline, prompt engineering)

- **Sam Kovac** - ML Engineer, 1.5 years. Honestly the strongest technical person on the team, maybe by a wide margin. Built our entire inference pipeline. Understands the LangChain/LangGraph stack better than anyone.

  One thing I should flag. Sam's been building what he describes as a "personal project" in the recipe recommendation space. A couple people on the team mentioned it to me separately. I looked at his public GitHub and it's... adjacent to what we do. Not a copy, but adjacent. He's open about it, doesn't seem to think it's a conflict. I never pushed on it because honestly I needed him shipping, and he's the only one who can maintain the inference pipeline. Flagging it for you to handle as you see fit.

  Also: Sam's process is fast but loose. The AI/ML squad has been merging without code review because Sam doesn't like the overhead and the other two defer to him. It works until it doesn't.

- **Lena Zhao** - ML Engineer, 8 months. Technically sound but defers to Sam on almost everything. I think she has more in her than she shows but the dynamic with Sam doesn't leave room for it.

- **Tyler Brooks** - Junior ML Engineer, 3 months. Eager. Sam's been assigning him work directly, which isn't how the other squads operate. Tyler thinks Sam walks on water.

- **James Park** - Data Engineer, ~1 year. Manages our data pipeline and recipe database. Quiet, does good work, easy to forget about. Has been asking about ML opportunities, which I think means he wants to move to Sam's squad.

---

A few general notes:

The team is rattled. I won't go into why I left but they know it wasn't entirely my choice, and some of them are reading the tea leaves. Your first couple weeks matter a lot for retention.

We don't have a formal on-call rotation. When things break, whoever notices first (usually Sam or Raj) fixes it. This has mostly worked because our user base is small but it's not going to scale.

There's no CI/CD to speak of. Raj set up a basic GitHub Actions pipeline that runs tests and deploys to a staging environment, but production deploys are manual. Sam usually just deploys the ML stuff directly.

Good luck. They're good people. They just need direction.

Dana
