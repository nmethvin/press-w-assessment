```
#incident-response Slack channel
Pinned message
Date: 2 weeks ago
```

**Incident: Recipe suggestions ignoring user pantry/equipment constraints**

**Duration:** ~6 hours (estimated, we don't have exact start time)

**What happened:**
Multiple beta users reported the assistant was recommending recipes requiring equipment they'd previously said they didn't own. One user who had specified "no oven" was told to make a roasted chicken. Another was recommended a blender smoothie recipe after telling the bot they only had a stovetop and a pan.

**How we found out:**
A beta user tweeted about it. Marcus saw the tweet and Slacked the team. Sam confirmed he could reproduce the issue about 30 minutes later.

**Root cause:**
Unclear. Sam thinks it was a prompt regression introduced when he updated the system prompt to improve personality (Marcus had asked for more opinionated responses). The equipment-checking instructions may have been inadvertently weakened or moved below the context window. No diff was reviewed before the change went live.

**Resolution:**
Sam rolled back the system prompt to the previous version. No formal verification that the issue was fully resolved - we spot-checked a few queries and they seemed fine.

**Action items:**
- [ ] Add tests for equipment constraint checking (assigned: Sam, not started)
- [ ] Set up monitoring/alerting for constraint violations (assigned: Raj, not started)
- [ ] Review prompt change process (assigned: ???, not started)
