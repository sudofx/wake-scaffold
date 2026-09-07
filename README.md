# Wake Scaffold

**A persistence protocol for stateless AI agents.**

Wake Scaffold explores a simple question:

> Can a sequence of stateless AI model invocations behave like one continuous, accountable agent? - See [`IDENTITIES.md`](IDENTITIES.md)

The model itself has no memory between wakes. Each invocation starts with a fresh context. The only continuity comes from what previous wakes deliberately wrote to durable state.

Wake Scaffold provides the structure, rules, and mechanical checks for making that continuity useful.

It is **not primarily an LLM wrapper, chatbot, or conventional RAG memory system**. It is an experiment in building persistent state around a stateless model.

## The core idea

A wake is temporary.

The state is durable.

```text
                 ┌─────────────────────┐
                 │    Fresh model      │
                 │     invocation      │
                 └──────────┬──────────┘
                            │
                       read state
                            │
                            ▼
                 ┌─────────────────────┐
                 │  Identity / Rules   │
                 │  Memories           │
                 │  Commitments        │
                 │  Hypotheses         │
                 │  Evidence           │
                 │  Recent synthesis   │
                 └──────────┬──────────┘
                            │
                         reflect
                            │
                            ▼
                 ┌─────────────────────┐
                 │       Act           │
                 │   use tools /       │
                 │   do the work       │
                 └──────────┬──────────┘
                            │
                       record results
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Durable state     │
                 │                     │
                 │   journal           │
                 │   memories          │
                 │   commitments       │
                 │   evidence          │
                 │   hypotheses        │
                 │   growth            │
                 └─────────────────────┘
                            │
                            ▼
                     next wake starts
                     from this state
```

The model is replaceable.

The persistent state is the continuity layer.

---

## Why this exists

Most AI agents are implicitly continuous because the application keeps their conversation, state, or process alive.

That assumption disappears when an agent is deliberately run as a sequence of independent executions:

```text
wake 1 → process exits
wake 2 → completely fresh process
wake 3 → completely fresh process
...
```

Without an external state layer, there is no reason for wake 3 to know what wake 1 learned, promised, tested, built, or discovered.

Wake Scaffold treats that external state as a first-class part of the agent.

The goal is not to pretend that the model itself has persistent memory.

The goal is to make persistence explicit, inspectable, and recoverable.

---

## What survives between wakes?

Not everything should be treated as "memory."

Wake Scaffold separates different kinds of durable state because they have different meanings and different rules.

```text
core_identity/
  identity.md          Who the agent is
  rules.md             Constraints it must follow
  failure_modes.md     Known failures and their fixes

core_memories/
  index.md             Curated high-level understanding
  commitments.json     Promises and their status
  semantic_memory.json Small set of formative lessons
  growth_plan.json     Capabilities being developed
  hypotheses.json      Claims being tested
  epistemic_state.json Observation → claim → test → outcome

core_workspace/
  journal/             Immutable record of what happened
  tools/               Tools the agent has built
  tool_runs.json       Evidence from actually running those tools

core_synthesis/
  ideas/               Per-wake reflection artifacts
  daily/               Mechanical daily indexes and summaries

core_persona/
  blog/                Public-facing output produced by the agent
```

The exact layout is deliberately filesystem-based and human-readable.

You can inspect it with ordinary tools.

You can version it with Git.

You can back it up.

You can move an identity to another machine.

You can replace the model provider without replacing the state.

---

## History is not memory

One of the central design principles is:

```text
What happened?
      ≠
What do I currently believe?
```

The journal is the historical record.

It records what a wake actually did, what it observed, what changed, and what happened as a result.

Curated memory is different. It is the smaller set of information worth carrying into future reasoning.

This distinction matters because an indefinitely growing transcript is not a useful memory system.

The journal can grow without bound while the state loaded into an ordinary wake remains deliberately small.

---

## Evidence is not a claim

The same principle applies to knowledge.

A model saying:

> "I built the tool."

is not evidence that the tool works.

Wake Scaffold therefore distinguishes between:

```text
code written
     ↓
code executed
     ↓
observable result
     ↓
evidence
     ↓
claim
```

For example, a capability in `growth_plan.json` cannot be considered complete merely because the agent wrote the code for it. A real tool-run result must exist as evidence.

Likewise, a hypothesis cannot simply be marked true because the model decided it was true.

The system is intentionally biased toward:

**what actually happened over what the model says happened.**

---

## Hypotheses and self-experimentation

`hypotheses.json` provides a small mechanism for testing beliefs rather than merely recording them.

A hypothesis contains:

- a specific claim or prediction
- a test method
- evidence
- a conclusion

This creates a simple loop:

```text
observation
    ↓
claim
    ↓
prediction
    ↓
test
    ↓
evidence
    ↓
conclusion
    ↓
revision
```

This is separate from the growth plan.

A growth project asks:

> **Can I build this?**

A hypothesis asks:

> **Is this true?**

That distinction is useful when an agent is both building things and trying to learn from its own behavior and environment.

---

## Commitments are not memories

A commitment is a promise that needs to survive the wake in which it was made.

The commitments ledger therefore has stronger rules than ordinary memory.

An agent can:

- create a commitment
- move its status forward
- record progress and notes

It cannot silently delete a commitment or rewrite its history.

This turns promises into durable state rather than leaving them buried in a previous conversation.

---

## The wake cycle

A normal wake is deliberately small and structured.

Conceptually:

```text
1. Load bounded persistent state
2. Reflect on what changed
3. Review relevant evidence, commitments, hypotheses, and limitations
4. Decide what to do
5. Perform the work
6. Record what actually happened
7. Apply permitted state changes
8. Write one immutable journal entry
```

The reflection is part of the visible artifact produced by the wake. It is not hidden chain-of-thought; it is a concise, inspectable summary of what changed, what was learned, and what matters for the next wake.

The result is a system where each wake is disposable, but the work is not.

---

## Bounded recall

The journal can grow indefinitely.

The model should not have to read the entire journal every time.

Wake Scaffold therefore uses a layered persistence model.

### Always-loaded state

Small, bounded state is read into every wake:

- identity
- rules
- commitments
- curated semantic memories
- current growth projects
- relevant hypotheses
- the current index
- recent tool evidence

### Detail state

The full historical record remains available but is not automatically loaded into every prompt:

- immutable journal entries
- older tool runs
- historical blog posts
- older evidence
- previous synthesis artifacts

### Synthesis state

Reflection and summary artifacts provide navigation and compression without destroying the underlying history.

The principle is:

> **Compress for recall; preserve for auditability.**

Nothing needs to be forgotten merely because it is no longer loaded into the next prompt.

---

## Self-editing with boundaries

An agent that can write to its own state can also corrupt its own state.

Wake Scaffold therefore does not give the model unrestricted filesystem authority.

Different pieces of state have different permissions.

For example:

| State | Agent can modify? | Principle |
|---|---:|---|
| Current focus | Yes | Replaceable working state |
| Known limitations | Yes | Append-only |
| Commitments | Limited | No silent deletion or rewriting |
| Semantic memory | Limited | Small bounded set |
| Growth plan | Limited | Evidence-backed progression |
| Hypotheses | Limited | Evidence required for resolution |
| Rules | No | Human-controlled by default |
| Identity name/purpose | No | Human-controlled |
| Immutable journal | Append only | Historical record |

The important idea is not that the model is trusted.

It is that the system tries to make certain classes of mistakes mechanically difficult.

---

## Tools: writing code is not running code

The agent can create small tools in its workspace.

But:

```text
write tool
    ≠
tool works
```

`tool-write` only writes the file.

`tool-run` actually executes an existing Python tool and records:

- exit code
- stdout
- stderr

That result becomes evidence available to subsequent wakes.

Tool execution is deliberately constrained with limits on execution time, output size, environment inheritance, and working directory.

This is a best-effort sandbox, not a security boundary or container.

---

## Model-provider independence

Wake Scaffold does not make the model provider part of the persistence architecture.

Providers implement a common interface, with support for multiple backends and a mock provider for testing.

The important abstraction is:

```text
              ┌───────────────┐
              │  Wake Scaffold │
              └───────┬───────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
       OpenAI      Anthropic    Gemini
          │           │           │
          └───────────┼───────────┘
                      │
                   Ollama
```

The model is an interchangeable reasoning engine.

The filesystem is the persistent state.

This means the same identity can, in principle, survive a change of model provider.

---

## Identity lifecycle

An identity is a complete persistent state, not just a name.

The active identity lives under `memory/`.

It can be archived and a new identity can be created from `base_memory/`:

```bash
python wake.py archive --as bob

python wake.py new \
  --name "Ada" \
  --purpose "Build and test small, repeatable research tools."
```

Or both operations can be performed together:

```bash
python wake.py reset \
  --archive-as bob \
  --name "Ada" \
  --purpose "Build and test small, repeatable research tools."
```

Archives are preserved rather than rewritten by the wake loop.

A new identity starts with a clean journal, commitments, memories, growth plan, and public output.

This makes identity itself a persistent, versionable artifact.

---

## What this is — and isn't

### It is

- A persistence layer for stateless AI agents
- A filesystem-based state model
- A framework for durable commitments and memories
- An experiment in evidence-backed agent continuity
- A way to separate historical record from current understanding
- Vendor-agnostic with respect to the model provider
- Human-readable and Git-friendly
- Deliberately small and inspectable

### It isn't

- A claim that an LLM is conscious
- A guarantee of genuine long-term memory
- A conventional vector-database RAG system
- An autonomous agent with unrestricted access to the host
- A secure sandbox
- A perfect cognitive architecture
- Proof that persistent identity has "emerged"

The project is experimental.

The interesting question is whether sufficiently structured longitudinal state can produce useful continuity from otherwise stateless inference.

---

## Repository structure

At the top level:

```text
wake-scaffold/
├── memory/                 # Active persistent identity
├── base_memory/            # Seed template for new identities
├── identities_archive/     # Archived identities
├── providers/              # Model-provider implementations
├── tests/                  # Tests using temporary state
├── wake.py                 # Wake-cycle orchestrator
├── config.yaml             # Runtime configuration
├── requirements.txt
└── .github/workflows/
    └── wake.yml            # Scheduled wake
```

The active `memory/` directory is intentionally ordinary files rather than a specialized database.

That is part of the experiment.

---

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Install the SDK for the provider selected in `config.yaml`.

For example:

```bash
pip install google-genai
```

or:

```bash
pip install anthropic
```

or:

```bash
pip install openai
```

Ollama does not require a Python provider SDK.

### 2. Configure credentials

```bash
cp .env.example .env
```

Add the API key for the provider you intend to use.

Only the selected provider needs credentials.

### 3. Configure the identity

Edit:

```text
memory/core_identity/identity.md
memory/core_identity/rules.md
```

Set the identity, purpose, constraints, and other initial state you want the agent to inherit.

### 4. Run a wake

```bash
python wake.py
```

The model gets a fresh process and context, reads the persistent state, performs one wake, and writes its results back to disk.

### 5. Validate the state

```bash
python wake.py validate
```

Validation checks the expected filesystem structure, JSON ledgers, and persisted wake history without changing the state.

### 6. Inspect what happened

Look at:

```text
memory/core_workspace/journal/
memory/core_memories/commitments.json
memory/core_memories/semantic_memory.json
memory/core_workspace/tool_runs.json
```

The journal is the authoritative record of the wake.

### 7. Schedule future wakes

The included GitHub Actions workflow can run wakes on a schedule.

At that point the system becomes:

```text
scheduled wake
      ↓
fresh process
      ↓
read persistent state
      ↓
reflect + act
      ↓
write persistent state
      ↓
process exits
      ↓
...
      ↓
next scheduled wake
```

---

## Testing

The test suite exercises the state-management mechanics without requiring a live model or API key.

```bash
python tests/test_wake.py
```

Tests use temporary memory directories rather than the real active identity.

The suite covers things such as:

- state validation
- self-edit mechanics
- reflection and journal flows
- fallback blog generation
- tool execution
- tool-run evidence
- subprocess environment restrictions
- working-directory restrictions

The mock provider makes it possible to exercise the wake machinery deterministically.

---

## Design principles

Wake Scaffold is built around a few simple rules.

### 1. Persistence should be explicit

If something needs to survive a wake, it should exist in durable state.

### 2. History should be preserved

The system should record what actually happened rather than continuously rewriting the past.

### 3. Current understanding should remain curated

The next wake should not need to ingest the entire history.

### 4. Evidence should outrank assertions

A model claiming that something happened is not the same as evidence that it happened.

### 5. Different state deserves different rules

Identity, commitments, memories, hypotheses, evidence, and history are not interchangeable.

### 6. Model providers should be replaceable

The persistence architecture should not depend on one LLM vendor.

### 7. Humans should retain control over foundational state

Rules and core identity properties are human-controlled by default.

### 8. Mechanical guarantees are better than instructions

Whenever possible, enforce an invariant in code instead of merely telling the model to behave.

### 9. Preserve detail even when compressing recall

A summary can replace what is loaded into context.

It should not replace the underlying evidence.

### 10. Be honest about limitations

A workaround is not a success if it merely violates another constraint or misrepresents what happened.

---

## The experiment

The deeper motivation behind Wake Scaffold is not to build a particular product.

It is to investigate what happens when you take a model with no built-in continuity and repeatedly place it in the same persistent environment.

Each invocation is stateless.

The state is longitudinal.

The model can change.

The identity's accumulated record remains.

That creates an interesting separation:

```text
               transient
              intelligence
                   │
                   ▼
            ┌─────────────┐
            │    wake     │
            └──────┬──────┘
                   │
                   ▼
          persistent state
                   │
                   ▼
            next invocation
```

If useful behavioral continuity emerges, it should come from the interaction between repeated inference and structured longitudinal state—not from pretending that a single model context lasts forever.

That is the experiment.

---

## Status

This is an active experiment rather than a finished framework.

The architecture is intentionally conservative in some places and primitive in others.

For example, `semantic_memory.json` is a small curated memory rather than a sophisticated relevance-triggered associative memory system. The journal is append-only rather than intelligently compressed. Tool execution has best-effort restrictions rather than a hardened sandbox.

Those limitations are intentional in the sense that they keep the system understandable enough to study.

The project can become more sophisticated later.

First, it should remain understandable.

---

## License

MIT

