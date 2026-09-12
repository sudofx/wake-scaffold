[Repository](https://github.com/sudofx/wake/tree/master) | [Blog](https://htmlpreview.github.io/?https://raw.githubusercontent.com/sudofx/wake/refs/heads/master/memory/core_persona/blog/html/index.html)

## Mission

**Scorched Earth: rebuild the entire project from scratch.** Ignore all previous architectural, folder, file, or implementation constraints. Keep only ideas that serve this question:

> **Can durable state plus mechanical epistemic/governance constraints turn ephemeral model calls into one longitudinal, auditable process?**

The model is disposable; **state, commitments, evidence, rules, and history are durable**. The experiment is whether that externalized continuity is sufficient to make many independent model invocations behave as one accountable process.

The system should demonstrate:

- continuity without persistent model memory
- durable commitments across model replacement
- mechanically enforced governance/invalid-transition rejection
- evidence-backed, revisable beliefs
- crash/recovery from the last valid state
- model interchangeability
- complete auditability
- long-running coherence across many fresh sessions
- constrained, reviewable autonomy

### The experiment must prove

1. **Fresh-session continuity:** kill all model/context; a new invocation continues solely from durable state.
2. **Causal state:** changing persisted state changes subsequent behavior.
3. **Commitment persistence:** Model B inherits obligations created by Model A without human reminder.
4. **Mechanical constraints:** deliberately attempt an invalid action/state transition; the system rejects/prevents it.
5. **Evidence lifecycle:** claims accumulate evidence and can later be maintained, revised, or retracted based on that record.
6. **Recovery:** terminate/corrupt an invocation mid-cycle; restart from the last valid durable state.
7. **Audit reconstruction:** an independent observer with only durable state/history can determine:
   - objective
   - beliefs
   - commitments
   - supporting evidence
   - reasons for state changes
   - model invocation responsible for each change
8. **Longitudinal coherence:** demonstrate dozens/hundreds of fresh invocation cycles, not merely one successful handoff.

The architecture should make these properties **system guarantees where possible**, rather than instructions buried in prompts.

## Product / UX

Timezone: **America/Los_Angeles**

Automated cron jobs should execute wake cycles and produce durable output.

I need to read the results anywhere on **iPhone 12 mini, iPad, and MacBook**.

Preferred presentation:

- **Human-facing report/journal:** concise, natural language, approachable to someone who doesn't understand the technical system.
- **Technical layer:** links into detailed state, evidence, decisions, logs, metrics, and raw wake-cycle data.
- Ideally build a killer web UI that feels like a **blog/journal**, with progressive disclosure into rich technical/data views and graphs.
- Desktop preference: Markdown.
- Mobile preference: HTML/web.
- Browser-rendered Markdown is ideal if practical.
- Existing `htmlpreview.github.io` approach is acceptable.

Think **blog → laboratory notebook → underlying evidence/data**.

## Cost / Models

**Budget: $0.**

I currently have:
- Gemini: **20 free API calls/day** — use this by default.
- Claude Desktop: free tier, no paid subscription; currently subject to its session quota.
- ChatGPT Desktop: free tier, no paid subscription; currently subject to its session quota.

Design the model interface/provider layer so other major vendors/models can be added later without redesigning the core system.

Optimize aggressively for free-tier constraints, minimizing unnecessary model calls.

## Personality / Design

I'm **Gen-X and proud of it**. Give the project that flavor in:

- visual design
- language
- UX
- public-facing reports
- attitude
- code comments/documentation where appropriate

But compartmentalize it:

**Public persona:** fun, irreverent, distinctly Gen-X.  
**Lab/system:** serious, rigorous, scientific/technical.

Do not let personality compromise experimental integrity.

## Deliverable

Produce the **complete working project** as:

`wake.zip` or if connected to the project folder with write access, modify the files directly.

I will delete everything in the existing project directory except `.git` history, then extract the ZIP contents into it.

Therefore, deliver a **self-contained replacement project**, not a patch or migration plan.

Make the architecture your own. Reuse existing concepts only when they genuinely help answer the mission.

The final system should make the core hypothesis **demonstrable rather than merely described**.