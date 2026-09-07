# Wake Scaffold

> A persistence protocol for stateless AI agents.

Wake Scaffold gives a stateless language model a durable identity, history, commitments, beliefs, and evidence without requiring the model itself to retain memory.

Each wake starts cold. The agent reconstructs its continuity from an explicit, human-readable filesystem.

The result is not simply "AI memory." It is an attempt to answer a deeper engineering question:

**How can a sequence of individually stateless model invocations behave like one continuous, accountable agent?**

---

## The idea

A language model does not inherently remember what happened yesterday.

Wake Scaffold does not try to change that.

Instead, it treats the filesystem as the agent's persistent state.

On every wake, the model reads a small amount of durable state, performs work, records what happened, produces evidence where appropriate, and updates the state that should survive into the next wake.

Conceptually:

```
                    ┌───────────────────┐
                    │   Previous State  │
                    │                   │
                    │ identity          │
                    │ rules             │
                    │ commitments       │
                    │ memories          │
                    │ hypotheses        │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │       WAKE        │
                    │                   │
                    │ reconstruct       │
                    │ reflect           │
                    │ plan              │
                    │ act               │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │      EVIDENCE     │
                    │                   │
                    │ observations      │
                    │ tool results      │
                    │ outcomes          │
                    │ discoveries       │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   Durable State   │
                    │                   │
                    │ journal           │
                    │ memories          │
                    │ commitments       │
                    │ beliefs           │
                    │ growth            │
                    └─────────┬─────────┘
                              │
                              │ next wake
                              ▼
                         ┌─────────┐
                         │  WAKE   │
                         └─────────┘
```

The model is ephemeral.

The continuity is not.

---

## Why this exists

Most LLM applications treat memory as one of two things:

1. Put previous conversation into the next prompt.
2. Store chunks in a vector database and retrieve similar text later.

Those approaches are useful, but they don't answer several harder questions:

- What does the agent consider part of its identity?
- What promises has it made?
- Which beliefs are hypotheses rather than facts?
- What has actually been verified?
- What happened, as opposed to what the agent currently believes happened?
- How does an agent change its beliefs?
- How can an agent modify itself without silently rewriting its own history?
- How can a human audit the evolution of an autonomous system?
- How can continuity survive a model change or a completely fresh process?

Wake Scaffold treats these as different problems.

Memory is only one component of persistence.

---

## Core principles

### 1. The model is stateless

Every wake should be able to start from a fresh model context.

Nothing about the model's previous inference is assumed to survive.

Continuity must therefore be reconstructed from durable artifacts.

This makes the persistence mechanism independent of any particular model provider.

---

### 2. History is not memory

The journal records what happened.

Semantic memory records what is worth carrying forward.

Those are deliberately different things.

A journal can grow indefinitely without forcing the entire history into every prompt.

The agent instead maintains a small "hot" representation of important durable knowledge while preserving the detailed historical record separately.

---

### 3. Different kinds of state should remain different

Wake Scaffold does not collapse everything into a single memory store.

The filesystem distinguishes concepts such as:

- **Identity** — who the agent is.
- **Rules** — constraints governing behavior.
- **Commitments** — promises, obligations, and unfinished work.
- **Semantic memory** — durable experiences or knowledge worth retaining.
- **Growth** — areas the agent intends to develop.
- **Hypotheses** — beliefs that should be tested rather than assumed.
- **Evidence** — observations and actual tool outcomes.
- **Journal** — an immutable chronological account of wakes.
- **Synthesis** — higher-level conclusions derived from accumulated experience.

This separation is intentional.

A promise is not a memory.

A hypothesis is not a fact.

A tool definition is not proof that the tool works.

A summary is not the historical record.

---

## Evidence over claims

One of the central ideas in Wake Scaffold is that **writing something down does not make it true**.

For example:

```
"I wrote a tool that fetches X"
```

is not equivalent to:

```
"I verified that the tool successfully fetched X"
```

The second statement requires evidence.

The same principle applies to beliefs and hypotheses.

A useful epistemic cycle looks like this:

```
Observation
    │
    ▼
Claim
    │
    ▼
Prediction
    │
    ▼
Test
    │
    ▼
Outcome
    │
    ▼
Revision
```

The objective is not to make the agent sound certain.

The objective is to give the agent a mechanism for becoming **less wrong over time**.

---

## The wake lifecycle

A typical wake follows a sequence like:

```
1. Load durable state
        ↓
2. Reconstruct current context
        ↓
3. Review commitments and open work
        ↓
4. Review relevant memories and hypotheses
        ↓
5. Reflect on recent evidence
        ↓
6. Decide what to do
        ↓
7. Execute work and tools
        ↓
8. Record observations and outcomes
        ↓
9. Update durable state
        ↓
10. Append an immutable journal entry
        ↓
11. Periodically synthesize accumulated experience
```

The important distinction is between **thinking about an action** and **recording evidence that the action actually happened**.

---

## The filesystem is the persistence layer

Wake Scaffold deliberately uses ordinary files rather than requiring a specialized memory database.

A workspace might look conceptually like:

```
workspace/
├── identity.md
├── rules.md
├── commitments.json
├── semantic_memory.json
├── growth.json
├── hypotheses.json
├── index.md
│
├── journal/
│   ├── 000001.md
│   ├── 000002.md
│   ├── 000003.md
│   └── ...
│
├── evidence/
│   ├── ...
│   └── ...
│
├── tools/
│   ├── ...
│   └── ...
│
└── synthesis/
    ├── ...
    └── ...
```

The exact workspace structure may evolve, but the philosophy is stable:

**persistent agent state should be inspectable by humans.**

You should be able to open the workspace with a text editor and understand what the agent thinks it knows.

---

## Immutable history

The journal is append-only.

A past wake should not silently change because the current model has a different interpretation of events.

This gives the system two distinct layers:

```
Historical record
       │
       │ immutable
       ▼
"What happened?"

Current state
       │
       │ revisable
       ▼
"What do I currently believe?"
```

That distinction is important for auditing, debugging, and understanding belief changes.

It also makes it possible to investigate questions such as:

- When did the agent learn this?
- Why does it believe this?
- What evidence caused the belief to change?
- When did this commitment appear?
- What happened before the current state was synthesized?

---

## Curated memory

Not everything that happens deserves permanent space in the agent's active context.

Wake Scaffold therefore distinguishes between:

```
             Full history
                  │
                  ▼
        ┌───────────────────┐
        │     Synthesis     │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │  Curated memory   │
        │                   │
        │ small             │
        │ relevant          │
        │ durable           │
        └─────────┬─────────┘
                  │
                  ▼
              Next wake
```

The goal is not maximum recall.

The goal is **useful continuity under bounded context**.

---

## Identity

An agent needs more than a collection of memories.

It needs some durable representation of who it is supposed to be.

Identity is therefore treated separately from ordinary memory.

This allows the agent to carry forward things such as:

- its name or role
- its purpose
- stable characteristics
- long-term direction
- carefully defined aspects of self-description

At the same time, identity is not completely mutable.

An autonomous system should not be able to casually rewrite its own foundational constraints and then claim that the new version has always been true.

---

## Rules and constrained self-modification

Self-modifying agents introduce an obvious problem:

**Who gets to decide what the agent is allowed to change?**

Wake Scaffold uses explicit boundaries.

Some state can be updated by the agent.

Some state is constrained.

Some changes can require human review.

This creates a distinction between:

```
Agent-managed state
        │
        ├── commitments
        ├── memories
        ├── hypotheses
        └── selected identity state

Human-controlled state
        │
        ├── foundational rules
        ├── protected identity
        └── sensitive configuration
```

The objective is not to prevent change.

It is to make important change **visible, deliberate, and auditable**.

---

## Commitments

A conversation can contain an enormous amount of information.

A promise is different.

If an agent says:

> "I'll finish this tomorrow."

that should not disappear simply because the next model invocation has no conversational memory.

Commitments therefore have their own durable representation.

This makes obligations first-class state rather than incidental text buried in a transcript.

---

## Hypotheses

Agents frequently make assumptions without realizing they are assumptions.

Wake Scaffold gives hypotheses an explicit place to live.

A hypothesis can contain a lifecycle such as:

```
Hypothesis
    ↓
Prediction
    ↓
Test
    ↓
Evidence
    ↓
Outcome
    ↓
Confirmed / Rejected / Revised
```

This encourages a different kind of agent behavior.

Instead of:

> "I think X, therefore X is true."

the agent can reason:

> "I currently believe X. If X is true, I expect Y. I can test Y."

That is a much more useful foundation for autonomous learning.

---

## Tools and verification

Tools are treated as capabilities that need evidence.

Creating a tool is not enough.

The system distinguishes:

```
Tool exists
    ≠
Tool executed
    ≠
Tool succeeded
    ≠
Tool produced trustworthy evidence
```

This matters because autonomous agents can otherwise accumulate fictional capabilities very easily.

A model can write:

```
"the deployment succeeded"
```

without ever having performed a deployment.

Wake Scaffold tries to make actual execution and its result part of the durable record.

---

## Model-provider independence

Wake Scaffold is designed around the persistence architecture rather than a particular LLM.

The model is effectively an interchangeable reasoning engine operating over durable state.

The project supports multiple providers and can also use a mock provider for testing.

This is intentional.

If persistence is part of the agent architecture, it should not disappear when the underlying model changes.

The same durable workspace should conceptually be usable across:

```
Model A
   ↓
Model B
   ↓
Model C
   ↓
Model D
```

provided those models can interpret the protocol.

---

## Security

Wake Scaffold should not be confused with a complete security sandbox.

The project takes steps to constrain tool execution and protect sensitive environment information, but filesystem-level restrictions and subprocess controls are not equivalent to a hardened operating-system sandbox.

If you give an autonomous agent powerful tools, you should assume that the tool boundary needs independent security engineering.

The persistence protocol answers:

> "What does the agent remember and believe?"

It does not by itself answer:

> "What is the agent safely allowed to do?"

Those are separate problems.

---

## What this is not

Wake Scaffold is not:

- a vector database
- a replacement for an LLM
- a general-purpose agent framework
- a consciousness claim
- a guarantee of genuine machine memory
- a secure sandbox
- a magical solution to context windows
- a claim that the agent is literally the same computational process across wakes

The model remains stateless.

What persists is the **external record through which continuity is reconstructed**.

---

## A useful mental model

Think of a wake as a new instance of the same role reading the records left by previous instances.

```
                 INSTANCE 1
                     │
                     │ writes
                     ▼
              ┌──────────────┐
              │ Persistent   │
              │   Record     │
              └──────┬───────┘
                     │
                     │ reads
                     ▼
                 INSTANCE 2
                     │
                     │ writes
                     ▼
              ┌──────────────┐
              │ Persistent   │
              │   Record     │
              └──────┬───────┘
                     │
                     ▼
                 INSTANCE 3
```

Each instance is ephemeral.

The record provides continuity.

This is closer to **succession** than biological memory.

---

## Why a filesystem?

Because a filesystem has useful properties for this problem:

- Human-readable
- Version-controllable
- Easy to back up
- Easy to diff
- Easy to inspect
- Easy to migrate
- Model-provider agnostic
- Friendly to ordinary developer tooling
- Naturally compatible with append-only records
- Does not require a proprietary memory service

A database may eventually make sense for scale.

But a filesystem is an excellent primitive for making the architecture understandable.

---

## Design goals

Wake Scaffold prioritizes:

### Transparency

A human should be able to inspect the agent's durable state.

### Provenance

Important beliefs should be traceable to observations or evidence.

### Bounded context

The agent should not need its entire history on every wake.

### Continuity

Important identity, commitments, knowledge, and goals should survive process boundaries.

### Auditability

The historical record should remain available even as current beliefs change.

### Model independence

Persistence should not be tied to one model provider.

### Controlled self-modification

An agent should have room to grow without having unrestricted authority over its own foundations.

### Testability

The persistence layer should be usable independently of expensive model inference.

---

## Current limitations

This project is intentionally experimental.

Some of the hardest problems remain open.

### Memory curation

How should an agent decide what deserves long-term memory without either forgetting important information or accumulating endless noise?

### Compression

How can long histories be synthesized without introducing subtle factual distortions?

### Belief integrity

How can we prevent an LLM from confidently misinterpreting its own historical record?

### Identity continuity

At what point does a sequence of stateless invocations meaningfully constitute one persistent agent?

### Security

How should powerful autonomous tools be sandboxed safely?

### Multi-agent state

How should multiple agents share, fork, merge, or challenge persistent state?

### Formal semantics

Can the workspace format become a well-defined protocol rather than merely a convention?

These are not solved problems.

They are part of why the project exists.

---

## Toward an agent continuity protocol

The long-term direction is to treat the filesystem not simply as "memory," but as a protocol for agent continuity.

One possible future architecture is:

```
                 Immutable Events
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
     Commitments      Beliefs       Identity
          │             │             │
          ▼             ▼             ▼
       Reducer        Reducer       Reducer
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                  Current State
                        │
                        ▼
                     Next Wake
```

In such a system, current state would be a projection of an immutable event history.

That would make it possible to reconstruct not only:

> "What does the agent believe now?"

but also:

> "When did it begin believing this?"

and:

> "Which evidence caused that belief to change?"

That is a much more interesting problem than simply retrieving similar memories.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/sudofx/wake-scaffold.git
cd wake-scaffold
```

Install the project dependencies according to the instructions for your chosen environment/provider.

Then configure the desired model provider and workspace.

See the source and configuration files in the repository for the current provider-specific setup.

---

## Running a wake

The fundamental operation is a wake.

A wake starts with persistent state and ends by leaving persistent state for the next wake.

Conceptually:

```bash
wake
```

The exact invocation and available options may evolve as the project develops.

The important contract is:

```
cold start
   ↓
read state
   ↓
reason
   ↓
act
   ↓
record evidence
   ↓
persist state
   ↓
exit
```

The process can terminate.

The next wake can start fresh.

Continuity survives outside the process.

---

## Testing

The repository includes a mock provider so that core behavior can be tested without requiring a live model.

This is important because much of the system's correctness should not depend on whether an LLM happens to produce a particular answer.

The persistence machinery should be testable as ordinary software.

---

## Scheduling

A wake can be run periodically using the scheduling system appropriate to your environment.

For example:

```
cron
systemd timers
container schedulers
CI runners
cloud jobs
```

This makes a particularly simple long-running agent architecture possible:

```
                 Scheduler
                     │
                     ▼
                  Wake
                     │
                     ▼
                 Do work
                     │
                     ▼
              Persist state
                     │
                     ▼
                   Exit
                     │
                     │
                     └───────────────┐
                                     │
                                next schedule
                                     │
                                     ▼
                                    Wake
```

There is no daemon that must remain alive indefinitely.

---

## Project philosophy

Wake Scaffold is built around a simple premise:

> **A persistent agent does not necessarily need a persistent process.**

It may be enough to preserve the right artifacts between invocations.

But those artifacts need to be more disciplined than a transcript.

They need to distinguish:

- history from memory
- beliefs from evidence
- commitments from preferences
- capabilities from verified capabilities
- identity from temporary context
- current state from historical record

The project explores what happens when those distinctions become part of the agent's runtime architecture.

---

## Research questions

Wake Scaffold is ultimately an exploration of several questions.

### Can continuity emerge from succession?

If every model invocation starts with no internal memory, can a sufficiently structured external record produce stable long-term behavior?

### What should an agent remember?

Not everything that happened is useful.

What makes an experience formative?

### Can an agent maintain epistemic humility?

Can explicit hypotheses, predictions, tests, and outcomes make an autonomous system better at recognizing when it is wrong?

### Can identity be versioned?

Can an agent change over time while still maintaining a traceable history of that change?

### Can self-modification be accountable?

Can an agent evolve without being able to silently rewrite the foundations that constrain it?

### Can persistent agents be model-independent?

If the underlying model changes, what exactly needs to survive for the "same" agent to continue?

---

## Status

Wake Scaffold is experimental.

The architecture is intentionally small and inspectable.

It should be treated as a research and engineering scaffold rather than a finished autonomous-agent platform.

The interesting part is not whether the current implementation is the final answer.

It is whether this model of persistence provides a useful foundation for building agents that can:

```
remember
    +
commit
    +
act
    +
observe
    +
learn
    +
revise
    +
continue
```

without requiring a continuously running process or hidden model-specific memory.

---

## License

See the repository's license file for the current licensing terms.

---

## Contributing

The most valuable contributions are likely to be improvements to the persistence model itself:

- Better provenance
- Better memory curation
- Better belief revision
- Stronger evidence tracking
- Safer self-modification
- More rigorous state transitions
- Better testing
- Better provider abstraction
- Formalization of the workspace protocol
- Experiments with long-running agent continuity

If you find a way to make the agent **more accountable for what it claims to know**, that is probably more valuable than simply giving it more memory.

---

## The core idea

A language model forgets when its process ends.

That does not mean the agent has to.

If the right state is externalized, structured, versioned, and grounded in evidence, each new invocation can inherit the work of the previous one.

Not because the model remembers.

Because the **record remembers**.

And the deeper question is whether that record can be enough to turn a sequence of stateless computations into a useful, persistent, accountable agent.
