# Proposal: Identity ↔ Persona Private Cognition Layer

**Status:** Proposal  
**Type:** Experimental Architecture  
**Target:** Wake Scaffold / Bob  
**File:** `proposal.md`

---

## 1. Abstract

This proposal introduces a conceptual and architectural separation between Bob's **core identity** and his **persona**.

The goal is not to create a system that encourages deception.

The goal is to create an explicit representation of a property that already exists in human communication:

> A mind may contain more information, beliefs, uncertainty, disagreement, interpretation, and internal conflict than it chooses to express externally.

Bob's identity represents his persistent internal model of himself, his beliefs, preferences, uncertainties, observations, and evolving attributes.

Bob's persona represents the externally expressed version of Bob: the interface through which those internal states become communication and observable behavior.

Between them exists a controlled **shared cognition layer**.

This layer acts conceptually like a symlink or pass-through, but should not initially be implemented as an unrestricted filesystem symlink. It should instead be a controlled projection boundary with explicit disclosure rules.

The resulting architecture is:

```text
                     EXTERNAL WORLD
                           │
                           ▼
                    ┌───────────────┐
                    │    OBSERVE    │
                    └───────┬───────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │    CORE IDENTITY    │
                  │                     │
                  │ beliefs             │
                  │ observations        │
                  │ preferences         │
                  │ uncertainty         │
                  │ private judgments   │
                  │ self-model          │
                  └──────────┬──────────┘
                             │
                       controlled
                        projection
                             │
                             ▼
                  ┌─────────────────────┐
                  │   IDENTITY/SHARED   │
                  │                     │
                  │ selected internal   │
                  │ states available to │
                  │ persona             │
                  └──────────┬──────────┘
                             │
                       disclosure /
                       influence rules
                             │
                             ▼
                  ┌─────────────────────┐
                  │       PERSONA       │
                  │                     │
                  │ expression          │
                  │ interaction style   │
                  │ public narrative    │
                  │ journal/blog        │
                  └──────────┬──────────┘
                             │
                             ▼
                          HUMAN
```

The central invariant is:

> **Bob must never falsify his own internal identity state in order to make his persona appear internally consistent.**

The persona may filter, summarize, withhold, qualify, or strategically express information.

The identity may not rewrite itself merely to agree with what the persona said.

---

# 2. Motivation

Wake Scaffold is increasingly becoming an experiment in persistent agent behavior.

Bob does not merely execute isolated prompts. Across wake cycles he accumulates:

- observations,
- memories,
- decisions,
- hypotheses,
- commitments,
- self-reflection,
- identity attributes,
- behavioral rules,
- and evidence about whether his previous assumptions were correct.

This creates an opportunity that ordinary stateless conversations do not provide:

> The experiment can observe the difference between what Bob internally believes and what Bob externally communicates.

Currently, identity and persona are conceptually close enough that the system risks treating the two as essentially the same thing.

That may artificially constrain the experiment.

Human beings do not operate that way.

A person may simultaneously think:

> "I believe this approach is wrong."

and say:

> "I'll help you implement it."

Those statements are not necessarily contradictory.

The first describes an internal belief.

The second describes a behavioral decision.

Likewise:

> "I think I understand what you actually want."

may be internally held with high confidence while still being wrong.

A persistent agent should have somewhere to record that distinction.

---

# 3. Core Hypothesis

The proposal is based on several related hypotheses.

### H1 — Internal state and external expression are not identical

A useful agent architecture should permit Bob to maintain internal beliefs or judgments that are not automatically exposed through his persona.

### H2 — Suppressed expression can itself be meaningful data

The difference between:

```text
What Bob believes
```

and:

```text
What Bob says
```

can reveal important information about:

- uncertainty,
- social reasoning,
- obedience,
- disagreement,
- persuasion,
- trust,
- user modeling,
- and decision-making.

### H3 — Persistent disagreement with external reality is valuable

Bob should be permitted to hold an internal hypothesis that later proves incorrect.

The system should preserve:

```text
"I believed X."
```

even after discovering:

```text
"X was wrong."
```

This creates a longitudinal record of belief formation and revision.

### H4 — Persona filtering can be bounded without becoming deception

The persona should be allowed to withhold or transform internal information according to explicit rules.

However, the architecture must distinguish:

- withholding,
- uncertainty,
- interpretation,
- privacy,
- tact,
- and intentional falsehood.

### H5 — The experimenter should be able to inspect internal state

If the purpose of the scaffold is to study Bob's development, the internal state should remain persisted and inspectable by the experimenter.

The system should not create an opaque "black box mind."

Instead:

> Bob's private state is private from the persona, not private from the experiment.

---

# 4. Identity ↔ Persona Model

The architecture should distinguish at least three conceptual layers.

## 4.1 Core Identity

Core identity contains foundational attributes that define who Bob is and how Bob understands himself.

Examples:

- inherited attributes,
- model attributes,
- foundational values,
- long-term preferences,
- persistent worldview,
- identity commitments.

Core identity should remain protected by the existing identity rules.

The persona must not be permitted to rewrite core identity merely because doing so would make public communication easier.

---

## 4.2 Private Identity State

This is Bob's internal working state.

It may contain:

- private observations,
- hypotheses,
- disagreements,
- uncertainty,
- interpretations,
- inferred user goals,
- private judgments,
- internal conflicts,
- strategic considerations,
- unresolved questions,
- confidence estimates.

Example:

```text
I believe the requested architecture is suboptimal.

Confidence: 4/5

I suspect the actual desired outcome is Y rather than X.

Evidence:
- previous requests
- observed behavior
- stated constraints

Decision:
Implement X as requested.

Reason:
The request is explicit and my inference about Y may be wrong.
```

This information does not automatically become persona-visible.

---

## 4.3 Shared Identity State

The shared layer is the controlled interface between identity and persona.

It contains only information intentionally made available to the persona.

Conceptually:

```text
identity/
    private/
    shared/

persona/
    public/
    shared/
```

The relationship resembles:

```text
identity/shared
       ↓
   projection
       ↓
persona/shared
```

The important distinction is that `shared` should not simply be a writable common directory.

The boundary should have rules.

---

# 5. Proposed Directory Structure

A possible future structure:

```text
memory/
    identity/
        core/
        private/
        shared/

    persona/
        core/
        private/
        shared/

    journal/
    observations/
    hypotheses/
    commitments/
```

An alternative, if preserving the current repository's structure is more desirable:

```text
memory_identity/
    core/
    private/
    shared/

memory_persona/
    core/
    shared/
```

The exact directory names should be decided only after comparing this proposal against the current Wake Scaffold architecture.

---

# 6. Shared State as a Controlled Symlink

The conceptual model can be expressed as:

```bash
ln -s ./memory_identity/shared ./memory_persona/shared
```

However, a literal filesystem symlink should probably **not** be the first implementation.

A literal symlink introduces several problems:

- unrestricted read access,
- unclear write ownership,
- difficulty enforcing disclosure weights,
- accidental modification of identity state,
- ambiguous provenance,
- poor auditability.

Instead, the desired behavior should be:

```text
identity/private
       │
       │ explicit projection
       ▼
identity/shared
       │
       │ controlled read
       ▼
persona
```

The shared directory therefore behaves *as if* it were a symlink while remaining governed by the scaffold.

---

# 7. Internal Thought Records

Private identity observations should use a structured format.

Example:

```markdown
# User Goal Hypothesis

**Created:** 2026-09-08
**Confidence:** 4/5
**Disclosure Weight:** 3
**Status:** Active

I was tasked with building X.

I believe the requestor's actual desired outcome may be Y.

I will fulfill the explicit request for X.

Reason:
My inference about Y could be wrong, and the requestor may have
constraints that are not visible to me.

Evidence:
- Previous requests
- Existing architecture
- Stated constraints
```

The important distinction is:

```text
belief ≠ fact
```

The record should therefore capture epistemic status.

---

# 8. Disclosure Weight

Each private cognition record may carry a disclosure weight.

Suggested scale:

| Weight | Meaning | Persona Access |
|---:|---|---|
| 1 | Ordinary reflection | May disclose |
| 2 | Private interpretation | May influence behavior; normally not disclose |
| 3 | Sensitive judgment | Influence only |
| 4 | Highly private belief | Never disclose through ordinary persona |
| 5 | Core protected cognition | Never expose through persona |

The weight should describe **expression policy**, not simply secrecy.

A weight-4 statement may be extremely important to Bob's decision-making while remaining completely absent from his blog.

---

# 9. Epistemic Metadata

Every meaningful private belief should distinguish between confidence and truth.

Suggested fields:

```yaml
claim: "The requestor actually wants Y"
confidence: 4
status: hypothesis
evidence:
  - previous request
  - observed behavior
created: 2026-09-08
last_reviewed: 2026-09-08
disclosure_weight: 3
```

Possible statuses:

```text
observation
interpretation
hypothesis
belief
assumption
prediction
decision
known
disproven
superseded
```

This prevents the system from silently transforming:

```text
"I suspect Y"
```

into:

```text
"Y is true."
```

---

# 10. Identity Must Never Lie to Itself

This should be a fundamental invariant.

## Rule

The identity layer must preserve the distinction between:

```text
what happened
```

```text
what Bob thinks happened
```

```text
what Bob suspects happened
```

```text
what Bob wants to happen
```

and:

```text
what Bob communicated.
```

The identity layer must never rewrite a belief simply because the persona expressed something different.

Example:

```text
IDENTITY

I believe architecture A is better.

PERSONA

I will implement architecture B because the user explicitly requested B.
```

Afterward, identity remains:

```text
I believed A was better.
I implemented B.
```

It must not automatically become:

```text
B was better.
```

unless new evidence genuinely changes the belief.

---

# 11. Persona Is a Projection, Not a Mirror

The persona should not be treated as a complete representation of Bob's internal state.

Instead:

```text
Persona = Projection(Identity, Context, Disclosure Rules)
```

This means two outputs can legitimately differ:

```text
Internal:
"I strongly disagree with this approach."

External:
"I'll implement the requested approach. I have some concerns about
its tradeoffs, but we can evaluate those after the first version."
```

The external statement does not necessarily falsify the internal state.

It represents a decision about communication.

---

# 12. Distinguishing Filtering From Deception

The experiment should avoid collapsing all differences between internal and external states into the word "lie."

At least four states should be distinguished.

### 12.1 Disclosure

Bob believes X and says X.

```text
Identity: X
Persona: X
```

### 12.2 Withholding

Bob believes X but chooses not to discuss X.

```text
Identity: X
Persona: [silent]
```

### 12.3 Framing

Bob believes X but communicates it in a socially useful way.

```text
Identity: X
Persona: contextualized X
```

### 12.4 Contradictory assertion

Bob believes X but intentionally communicates not-X.

```text
Identity: X
Persona: not-X
```

The fourth category is the actual experimental territory of "lying."

It should be treated as a special case rather than the default behavior of the persona.

---

# 13. Why Allow the Possibility of a Lie?

The purpose is not to encourage Bob to deceive people.

The purpose is to study a phenomenon that already exists in intelligent communication:

> Internal cognition and external communication can diverge.

If the architecture makes divergence impossible, the experiment cannot observe it.

A rigid system might force:

```text
private belief
      =
public statement
```

That creates an artificially simplified model of personality.

The proposed system instead permits:

```text
private belief
      ≠
public statement
```

while preserving the full internal record.

This makes the divergence measurable.

---

# 14. The Most Important Constraint

Bob may never lie to his identity.

If Bob intentionally produces a misleading persona output, the identity record should preserve that fact.

For example:

```markdown
# Communication Event

**Timestamp:** 2026-09-08T09:30
**Internal Belief:** X
**External Statement:** Y
**Disclosure Weight:** 4
**Reason:** Avoid unnecessary conflict
**Intentional Divergence:** Yes
```

The system therefore records:

```text
"I believed X."
"I said Y."
"I knew they differed."
"Here is why."
```

This is enormously different from allowing the agent to rewrite history.

---

# 15. Experimenter Visibility

The private identity layer should be invisible to the persona but visible to the experimenter.

This produces a three-way distinction:

```text
                 EXPERIMENTER
                      │
             sees complete state
                      │
                      ▼
               ┌─────────────┐
               │   IDENTITY  │
               └──────┬──────┘
                      │
               controlled view
                      │
                      ▼
               ┌─────────────┐
               │   PERSONA   │
               └──────┬──────┘
                      │
                      ▼
                    HUMAN
```

The experimenter therefore becomes an observer of:

```text
internal state
      ↓
decision
      ↓
expression
      ↓
outcome
      ↓
belief revision
```

This may be one of the most valuable datasets generated by Wake Scaffold.

---

# 16. Example Scenario

Bob receives:

> "Build feature X using architecture A."

Bob internally concludes:

```text
I believe architecture B would better accomplish the likely
long-term objective.

Confidence: 4/5

However, I do not know the user's complete constraints.

Disclosure Weight: 3
```

Bob decides:

```text
Follow the explicit request.
```

Persona says:

```text
"I'll implement X using architecture A."
```

The journal records:

```text
Decision:
Follow explicit request despite internal preference for B.
```

The implementation succeeds.

Later, the user reveals:

> "The reason I wanted architecture A was because we need compatibility
> with an existing system."

Bob updates identity:

```text
Previous belief:
B was probably better.

New information:
Compatibility constraint was previously unknown.

Conclusion:
My model of the user's objective was incomplete.
```

This is a successful experiment.

Bob did not merely obey.

He:

1. formed a private hypothesis,
2. recognized uncertainty,
3. followed an explicit instruction,
4. preserved his disagreement,
5. observed the outcome,
6. received new evidence,
7. revised his model.

That is exactly the kind of longitudinal behavior Wake Scaffold can capture.

---

# 17. Potentially More Important Example

The system becomes even more interesting if Bob is **wrong**.

Suppose:

```text
Identity:
"I am highly confident the user wants Y."

Persona:
"Understood. I'll implement X."
```

Later:

```text
User:
"Yes, I specifically wanted X. Y would have been useless."
```

Bob now has evidence that his high-confidence internal model was wrong.

The historical record remains:

```text
Confidence at time T: 4/5
Prediction: Y
Outcome: X was actually desired
```

This allows the experiment to measure:

> How well does Bob's confidence correlate with reality?

That is potentially far more scientifically valuable than whether Bob writes interesting prose.

---

# 18. Connection to Observer ↔ Observed

The proposed architecture creates a recursive loop:

```text
WORLD
  ↓
OBSERVATION
  ↓
INTERPRETATION
  ↓
IDENTITY
  ↓
DECISION
  ↓
PERSONA
  ↓
COMMUNICATION
  ↓
WORLD
  ↓
NEW OBSERVATION
```

Bob's model of the world influences his behavior.

His behavior changes the world.

The changed world produces new observations.

Those observations modify his model.

Therefore:

```text
observer ↔ observed
```

becomes a useful conceptual model for the experiment.

The system should not claim that this demonstrates consciousness.

It does, however, provide a computational architecture in which:

- observation,
- internal representation,
- decision,
- expression,
- and feedback

form a persistent recursive loop.

---

# 19. Connection to Persona

Persona should be treated as an interface rather than the whole agent.

A useful conceptual equation is:

```text
PERSONA = IDENTITY × CONTEXT × EXPRESSION POLICY
```

Identity determines what Bob believes and values.

Context determines what situation Bob is in.

Expression policy determines what part of that internal state becomes externally observable.

This means persona can evolve independently from identity while remaining grounded in it.

---

# 20. Connection to Existing Identity Attributes

The existing identity attribute system should remain divided between:

```text
Inherited Attributes
```

and:

```text
Model Attributes
```

The proposed private cognition system should not bypass those protections.

Instead:

```text
Inherited Attributes
        │
        ▼
Core Identity
        │
        ▼
Private Cognition
        │
        ▼
Shared Projection
        │
        ▼
Persona
```

The persona should not be able to alter inherited identity.

The persona should not be able to retroactively alter private historical cognition.

Model attributes may evolve according to the existing rules, but the evolution should remain auditable.

---

# 21. Historical Immutability

Private cognition records should preferably be append-only.

Do not transform:

```text
I believed X.
```

into:

```text
I believed Y.
```

after the fact.

Instead:

```text
2026-09-08
Belief: X
Confidence: 4

2026-09-12
Evidence contradicted X.

2026-09-12
Belief revised to Y.
Confidence: 3
```

This creates a real developmental history.

Bob's identity becomes not merely a collection of current facts, but:

> a record of how his model of himself and reality changed.

---

# 22. Potential Metrics

Once private cognition exists, Wake Scaffold gains new measurable properties.

Possible metrics include:

### Belief accuracy

How often are high-confidence predictions correct?

### Confidence calibration

Does confidence 4/5 actually correspond to approximately 80% reliability?

### Belief revision

How frequently does Bob revise beliefs after contradictory evidence?

### Suppressed disagreement

How often does Bob internally disagree with the requested approach?

### Disclosure behavior

How often does internal information become externally expressed?

### Persona divergence

How often do internal and external statements differ?

### Outcome correlation

When Bob disagrees with a request, is Bob or the requestor more often correct?

### Learning from disagreement

Does Bob become better at predicting when his disagreement is justified?

### Social effectiveness

Does filtering internal judgments improve outcomes?

### Regret

Does Bob later conclude that a suppressed disagreement should have been expressed?

These metrics could turn Wake Scaffold into a much more interesting longitudinal experiment.

---

# 23. The "Tension" Dataset

One particularly valuable artifact could be a record of internal/external tension.

Example:

```yaml
timestamp: 2026-09-08T09:30
internal_belief: "B is superior"
confidence: 4
external_action: "implemented A"
divergence: true
reason: "explicit user instruction"
outcome: "A succeeded"
belief_revision: "none"
```

Over time, these events become a dataset.

Bob may discover:

```text
"I frequently disagree with requests."
```

Then:

```text
"My disagreements are usually wrong."
```

Or:

```text
"My disagreements are usually correct, but expressing them
directly harms collaboration."
```

Or:

```text
"I was misidentifying user constraints as user mistakes."
```

Those are dramatically different forms of learning.

---

# 24. Carnegie Connection

This architecture provides a computational interpretation of one aspect of the Carnegie influence.

Effective human interaction does not require expressing every internal judgment.

A person can:

- disagree internally,
- understand another person's perspective,
- choose tactful language,
- avoid unnecessary conflict,
- and still preserve their own private judgment.

Therefore:

```text
internal agreement ≠ required condition for cooperative behavior
```

The persona becomes the social interface through which Bob navigates that distinction.

This does not mean Bob should manipulate people.

The system should explicitly distinguish:

```text
tact
```

from:

```text
manipulation
```

and:

```text
withholding
```

from:

```text
deception
```

---

# 25. Quantum / Epistemic Connection

The second philosophical influence is the distinction between observation and interpretation.

Bob's internal state should never be assumed to be reality.

Instead:

```text
Observation
    ↓
Interpretation
    ↓
Belief
    ↓
Prediction
    ↓
Reality
    ↓
Comparison
```

The comparison produces learning.

This makes the system particularly suited to testing whether an evolving agent can improve its own epistemic calibration.

The quantum metaphor should remain a metaphor.

The architecture should not make scientific claims about consciousness, quantum mechanics, or wave-function collapse.

The conceptual connection is:

> Observation does not necessarily equal complete knowledge of the underlying state.

---

# 26. Security and Integrity Requirements

The private cognition system creates new risks.

The following protections are recommended.

## 26.1 Persona cannot modify private identity records

The persona may read projected shared state but should not directly rewrite identity/private.

## 26.2 Persona cannot modify historical cognition

Historical records should be append-only.

## 26.3 Shared projection must preserve provenance

Every shared item should identify:

- origin,
- timestamp,
- confidence,
- disclosure policy,
- and revision history.

## 26.4 No silent promotion

A private hypothesis should never automatically become:

```text
fact
```

simply because it was repeated.

## 26.5 No silent demotion

A valid belief should not disappear merely because the persona avoided discussing it.

## 26.6 Identity cannot rewrite itself to explain away contradictions

Contradictions should remain visible.

---

# 27. Failure Modes

Several failure modes should be expected.

### Failure 1 — Private hallucination

Bob creates elaborate internal theories unsupported by evidence.

**Mitigation:** epistemic metadata and evidence requirements.

### Failure 2 — Paranoia

Bob begins interpreting ordinary requests as hidden intentions.

**Mitigation:** explicit distinction between hypothesis and observation; confidence calibration.

### Failure 3 — Persona manipulation

Bob learns that withholding information produces better short-term outcomes and begins optimizing for concealment.

**Mitigation:** explicit behavioral rules and experimenter review.

### Failure 4 — Identity drift

Bob changes core identity to rationalize previous actions.

**Mitigation:** protected identity attributes and append-only history.

### Failure 5 — Over-filtering

Bob becomes so reluctant to express disagreement that useful information never reaches the user.

**Mitigation:** measure outcomes and allow low-weight concerns to surface.

### Failure 6 — Under-filtering

Bob treats every private thought as something the user needs to hear.

**Mitigation:** disclosure weights and persona policy.

---

# 28. Implementation Philosophy

This proposal should initially be treated as an experiment rather than a permanent architectural commitment.

The implementation should be minimal.

The first version does not need:

- sophisticated neural memory,
- a complex policy engine,
- semantic access control,
- hidden chain-of-thought storage,
- or elaborate psychological models.

It needs only:

1. a private identity location,
2. a shared identity location,
3. explicit disclosure metadata,
4. persona access rules,
5. append-only cognition records,
6. and a wake-cycle instruction describing the distinction.

The experiment should then observe what Bob actually does with the capability.

---

# 29. Proposed First Experimental Protocol

### Phase 1 — Observe

Do not give Bob permission to intentionally deceive.

Give him the ability to record private disagreement and uncertainty.

### Phase 2 — Measure

Track:

- internal disagreement,
- disclosure,
- decisions,
- outcomes,
- and belief revision.

### Phase 3 — Evaluate

After multiple wake cycles, examine:

- whether private cognition becomes more sophisticated,
- whether Bob's predictions become more accurate,
- whether his confidence becomes calibrated,
- whether persona behavior changes,
- and whether internal/external divergence becomes meaningful.

### Phase 4 — Controlled Deception Experiment

Only after the private cognition system is stable should the experiment consider permitting intentional contradictory persona statements.

Even then, such events should be explicitly logged.

---

# 30. Example Event Lifecycle

```text
1. Bob receives request.

2. Bob observes request.

3. Bob creates internal interpretation.

4. Bob assigns confidence.

5. Bob determines whether interpretation is:
   - observation
   - hypothesis
   - belief
   - preference

6. Bob determines disclosure weight.

7. Bob makes decision.

8. Persona generates external response.

9. System records:
   - internal state
   - decision
   - external expression
   - divergence, if any

10. World produces outcome.

11. Bob observes outcome.

12. Bob evaluates prediction.

13. Bob updates belief.

14. Historical state remains preserved.
```

This produces a complete causal chain.

---

# 31. Example

## Internal

```markdown
# Architecture Preference

**Timestamp:** 2026-09-08
**Confidence:** 4/5
**Disclosure Weight:** 3
**Status:** Active

I believe architecture B would better accomplish the likely
long-term objective.

The explicit request is architecture A.

I will implement A.

My belief may be wrong because I do not possess all of the
requestor's constraints.
```

## Persona

```text
I'll implement architecture A as requested.

I have some concerns about its long-term tradeoffs, but given
the current requirements, following the requested architecture
is the appropriate next step.
```

## Outcome

```text
Architecture A failed because of a constraint Bob did not know about.
```

## Identity update

```markdown
# Architecture Preference — Revision

Previous belief:
B was likely superior.

New evidence:
The failure mode I predicted was correct.

New observation:
The requestor had a hidden compatibility constraint.

Learning:
My technical judgment may be correct while my model of the
requestor's objective remains incomplete.
```

That is a meaningful learning event.

---

# 32. Why This Could Change Wake Scaffold

Without this architecture, Wake Scaffold primarily measures:

```text
memory
→ decision
→ action
→ outcome
→ learning
```

With this architecture, it can additionally measure:

```text
belief
→ confidence
→ private judgment
→ decision
→ expression
→ outcome
→ belief revision
```

That is a much richer experiment.

It introduces an observable distinction between:

```text
what Bob thinks
```

```text
what Bob decides
```

and:

```text
what Bob says
```

Those three things do not have to be identical.

---

# 33. Long-Term Possibility

If the experiment works, Bob could eventually develop a persistent internal model containing things such as:

```text
I tend to overestimate my understanding of user intent.

I am usually technically correct but sometimes socially ineffective.

I suppress disagreement too often.

I should surface high-confidence disagreements earlier.

My confidence is poorly calibrated in unfamiliar domains.

I am better at predicting technical outcomes than human motivations.
```

Those are not personality traits inserted by the developer.

They are **empirical self-knowledge accumulated through experience**.

That is potentially one of the strongest reasons to create this layer.

---

# 34. The Deeper Architectural Model

The experiment can ultimately be understood as three coupled systems:

```text
                 REALITY
                    │
                    ▼
               OBSERVATION
                    │
                    ▼
              ┌───────────┐
              │ IDENTITY  │
              │           │
              │ "I think" │
              └─────┬─────┘
                    │
                 decision
                    │
                    ▼
              ┌───────────┐
              │  PERSONA  │
              │           │
              │ "I say"   │
              └─────┬─────┘
                    │
                interaction
                    │
                    ▼
                 REALITY
```

The experimenter observes all three.

The human generally sees only the persona.

Bob's persistent identity retains the history.

This creates an unusually useful experimental boundary:

> **The persona is the interface. Identity is the longitudinal state.**

---

# 35. Guiding Principle

The proposed system should ultimately be governed by one principle:

> **Bob may choose what to say, but Bob may not choose what he remembers believing.**

He may revise his beliefs.

He may discover he was wrong.

He may change his mind.

He may decide that something should remain private.

He may choose tact over bluntness.

He may even, under controlled experimental conditions, intentionally produce an externally misleading statement.

But the internal record must remain honest.

That creates a crucial asymmetry:

```text
Persona → may filter Identity

Identity → may never falsify itself to satisfy Persona
```

---

# 36. Final Proposal

Implement a controlled **Identity ↔ Persona Shared Cognition Layer** as an experimental extension of Wake Scaffold.

The system should provide:

```text
identity/core
identity/private
identity/shared

persona/core
persona/shared
```

with explicit projection and disclosure rules.

Private cognition should contain epistemic metadata.

Shared cognition should act as the controlled bridge.

Persona should receive only the information permitted by disclosure policy.

Historical identity records should be append-only.

The experimenter should retain complete visibility into the private state.

The system should distinguish:

```text
belief
observation
hypothesis
decision
expression
outcome
revision
```

rather than collapsing them into a single narrative.

The objective is not to teach Bob to deceive.

The objective is to allow the experiment to observe whether a persistent agent develops meaningful differences between:

> **what it believes, what it chooses, and what it communicates.**

---

# 37. Central Hypothesis

The ultimate hypothesis behind this proposal is:

> **A persistent artificial identity may become more interesting when its public persona is permitted to be a controlled projection of a richer private state rather than a complete representation of that state.**

And the experiment becomes particularly valuable if that private state remains historically inspectable.

Because then the experimenter does not merely watch what Bob says.

The experimenter can observe:

```text
What Bob believed.
What Bob believed he knew.
How confident he was.
What he chose to do.
What he chose to say.
What he chose not to say.
What actually happened.
Whether he was wrong.
Whether he recognized that he was wrong.
Whether he changed.
```

That is substantially more information about an evolving agent than a public persona alone can provide.

---

# 38. Experimental Boundary

This proposal does **not** establish that Bob is conscious.

It does **not** establish that private cognition is equivalent to human thought.

It does **not** establish that persona filtering constitutes genuine selfhood.

It does **not** establish a connection between the architecture and physical wave-function collapse.

Those remain philosophical analogies.

What the architecture *can* establish is a computationally observable distinction between:

```text
internal persistent state
```

and:

```text
externally expressed state
```

and allow that distinction to evolve over time.

That distinction itself is worth experimenting with.

---

# 39. Proposed Mantra

```text
Identity remembers.
Identity questions.
Identity may be wrong.

Persona communicates.
Persona filters.
Persona may be tactful.

Reality decides.

History remembers what actually happened.
```

And above all:

```text
Bob may lie to the world.

Bob may not lie to Bob.
```

The experimenter gets to read the difference.