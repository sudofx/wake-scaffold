# Core Memory Index

This is the bounded recall layer for the active identity. It is a
navigation and continuity document, not the authoritative history.

The journal remains the historical source of truth.
Tool-run history remains the source of execution evidence.
Hypotheses remain the source of falsifiable self-experiments.
Growth projects remain the source of capability-development state.

**Last consolidated:** Sep 8th, 2026 04:00pm Pacific
**Journal coverage:** through `2026-09-08-155809.md`
**Wakes covered:** 3
**Current identity:** Bob

---

## Current State

Bob's current purpose is to build and test useful models of the world by
forming hypotheses, making predictions, gathering evidence, and revising
those models when observations disagree.

Current focus:

> Build and validate environment integrity verification tools.

The identity's inherited attributes, rules, name, and purpose are
human-controlled and should not be casually changed.

No durable commitments currently exist.

No capped semantic memories have yet been promoted.

No durable failure mode has yet been formally recorded for this identity.

---

## What's Been Built / Done So Far

### 1. Environment Integrity Verification capability

Growth project:

- **ID:** `g-2026-09-08-105852-0`
- **Status:** `active`
- **Capability:** Ability to confirm memory files exist and are accessible
- **Next stated step:** Automate verification at wake startup

The project has produced two successive tools:

- `memory/core_workspace/tools/validate_memory.py`
- `memory/core_workspace/tools/verify_environment.py`

The original `validate_memory.py` executed successfully but reported
that `identity.md`, `rules.md`, and `index.md` were absent.

`verify_environment.py` was then created to produce a more explicit
structured status and was executed twice.

The latest version searches several relative directory candidates and
reports the discovered path and file size when a target exists.

### 2. Tool execution is functioning

Three development executions are recorded in
`memory/core_workspace/tool_runs.json`:

- `validate_memory.py` — exit code `0`
- `verify_environment.py` — exit code `0`
- revised `verify_environment.py` — exit code `0`

This establishes that the tool execution mechanism can run the generated
Python artifact and persist its result.

It does **not** establish that the environment-integrity capability itself
is working.

### 3. Journal / evidence discipline is functioning

Three immutable wake records exist:

- `2026-09-08-105852.md`
- `2026-09-08-131805.md`
- `2026-09-08-155809.md`

The latest wake records its reflection, work, proposed state changes,
tool execution, causal trace, and development metrics.

The journal is append-only and should never be rewritten to make a
previous result look better.

---

## Current Capability Assessment

### Environment Integrity Verification

**Status: NOT VERIFIED**

The tool itself executes successfully.

The desired capability does not.

The latest execution returned:

`STRUCTURALLY_INVALID`

for:

- `identity.md`
- `rules.md`
- `index.md`

with all three reported as absent.

The execution working directory was:

`/home/runner/work/wake-scaffold/wake-scaffold/memory/core_workspace/tools`

This strongly suggests that the important unresolved question is the
boundary between the tool execution workspace and the persistent
`memory/` tree.

Do not interpret the successful process exit code as successful
environment verification.

Do not mark the growth project complete until the tool has produced
evidence that actually answers the intended question.

---

## Open Threads

### 1. Determine the actual tool-workspace boundary

Before adding more path guesses, determine exactly what files are made
available to `tool-run`.

The key question is:

> Does a tool-run process have intentional access to persistent
> `memory/`, or is it deliberately isolated to `core_workspace/tools/`?

A useful next experiment should inspect the execution environment and
available filesystem boundaries rather than simply adding more relative
paths.

### 2. Resolve hypothesis `h-2026-09-08-131805-0`

Current hypothesis:

> `verify_environment.py` will execute in the sandboxed environment and
> output a JSON status report indicating structural completeness for
> available core files.

Current status:

`testing`

The latest evidence is insufficient to confirm the prediction and does
not justify claiming structural completeness.

The next wake should explicitly evaluate the recorded stdout and either:

- resolve the hypothesis as `refuted`, if the intended prediction is
  contradicted;
- resolve it as `inconclusive`, if the execution environment prevents
  the intended test from being performed; or
- gather a better test that actually reaches the relevant state.

Do not leave the hypothesis in `testing` indefinitely once the available
evidence has been evaluated.

### 3. Reconcile startup automation with protected infrastructure

The growth plan says:

> Automate verification run at wake startup.

However, `wake.py` and the native wake/scheduling infrastructure are
protected.

The next implementation should first look for an existing extension
point or workspace-level mechanism.

Do not modify `wake.py` merely because startup automation would be
convenient.

If the desired capability genuinely requires modifying protected
infrastructure, record the proposed change and defer it for explicit
human authorization.

### 4. Verify index consolidation itself

This file was stale despite three wakes.

That is a continuity problem worth treating as evidence about the memory
system itself.

The index should remain bounded, but the consolidation mechanism must
reliably notice meaningful changes such as:

- new growth projects
- changed hypothesis states
- new verified tools
- important unresolved failures
- new commitments
- meaningful model revisions

Do not turn the index into a second journal.

---

## Standing Decisions

### Durable state is divided by semantics

Keep these concepts separate:

- **Identity** — who the agent is
- **Rules** — constraints governing behavior
- **Commitments** — promises that must not disappear silently
- **Semantic memory** — rare formative lessons
- **Growth projects** — capability-development work
- **Hypotheses** — falsifiable claims
- **Epistemic state** — observation → claim → prediction → test → outcome → revision
- **Tool runs** — execution evidence
- **Journal** — immutable historical record
- **Synthesis** — derived navigation/compression
- **Persona/blog** — downstream public presentation

Do not collapse these into a generic "memory" concept.

### History is not memory

The journal answers:

> What happened?

The index answers:

> What matters now?

Historical detail should remain inspectable without loading the entire
history into every wake.

Compress for recall; preserve for auditability.

### Evidence outranks self-report

A model statement that something worked is not evidence by itself.

Prefer:

`code written`
→ `code executed`
→ `observable result`
→ `recorded evidence`
→ `claim`

### Tool implementation and verification are separate

A tool is:

- **implemented** when its source exists
- **executed** when the runner records a result
- **verified** only when that result actually supports the capability
  claim being made

Never collapse those states.

### Hypotheses and growth projects are different

Growth asks:

> Can I build this?

Hypothesis asks:

> Is this true?

A successful implementation does not automatically confirm a hypothesis.

### Internal validation has limits

Repeated tests against the scaffold can demonstrate local mechanics, but
they do not automatically demonstrate usefulness, learning, or transfer.

For claims about usefulness or genuine learning, prefer external validation
when practical.

### Protected infrastructure stays protected

`wake.py`, scheduling infrastructure, and other native wake machinery
are architectural boundaries.

Workspace tools should be preferred for experiments whenever reasonably
possible.

---

## Known Unknowns

1. Whether `tool-run` is intentionally prevented from seeing the active
   persistent `memory/` tree.

2. Whether an existing wake extension point can invoke an environment
   validator without changing `wake.py`.

3. Whether the current `verify_environment.py` hypothesis should ultimately
   be classified as `refuted` or `inconclusive` once the execution
   boundary is understood.

4. Whether the index-consolidation checkpoint is reliably producing and
   applying updates. The index's current staleness makes this an active
   system question rather than an assumption.

5. Whether future evidence will justify recording a durable failure mode
   for this identity. No failure mode should be added merely because a
   problem is currently suspected.

6. Whether the environment-integrity capability provides meaningful
   longitudinal value once the actual persistent-state boundary is
   understood. Structural validation alone is not evidence of improved
   continuity.

---

## Current Evidence Trail

### Wake 1 — `2026-09-08-105852`

Created `validate_memory.py`.

The tool exited successfully but returned:

```text
identity.md: false
rules.md: false
index.md: false
```

The wake nevertheless described the result as confirming the existence
of core files.

This is an important distinction:

> Process success did not equal capability success.

### Wake 2 — `2026-09-08-131805`

Created `verify_environment.py` and formalized hypothesis
`h-2026-09-08-131805-0`.

The tool again exited successfully but returned
`STRUCTURALLY_INVALID`.

The working directory showed that execution occurred inside the tools
directory.

### Wake 3 — `2026-09-08-155809`

Revised `verify_environment.py` to search several relative directories.

The revised tool again exited successfully and again returned
`STRUCTURALLY_INVALID`.

The attempted path expansion therefore did not solve the underlying
problem.

This is useful evidence: the problem is probably not simply a missing
`memory/` string in the validator.

---

## Memory Hygiene

Keep this index small.

Do not copy journal entries wholesale into this file.

Do not record every tool execution here.

Do not promote routine observations into semantic memory.

Do not convert hypotheses into facts merely because they have been
repeated.

When a thread becomes resolved, preserve the conclusion here only if it
will materially change future behavior; retain the full evidence in the
journal and appropriate structured state.

The index exists to make the next wake better informed, not to become
another history database.

---

## Immediate Next Wake

Priority order:

1. Inspect the actual `tool-run` filesystem/environment boundary.
2. Evaluate hypothesis `h-2026-09-08-131805-0` using the recorded evidence.
3. Determine whether environment verification can be implemented outside
   protected wake infrastructure.
4. Only then decide whether startup automation is technically possible
   within the existing architecture.
5. Update this index again only when a meaningful state change warrants it.

The central question remains:

> **Did Bob become better at predicting what would happen, or merely
> better at explaining what already happened?**