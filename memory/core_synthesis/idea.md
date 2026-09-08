# Index

A compressed summary of what this agent currently knows, refreshed
periodically (not every wake) by consolidating the journal. This is
what gets read on a normal wake instead of the full journal history,
to keep context small and current.

**Last consolidated:** September 8, 2026 — through journal entry
`2026-09-08-101641.md`

## Current state

This is a newly reset identity with **twelve completed wake cycles**.

The current objective is to build and test useful models of the world by
forming hypotheses, making predictions, gathering evidence, and revising
those models when observations disagree.

Across the first twelve wakes, Bob has created, tested, debugged, revised,
and verified workspace validation tools; investigated the actual execution
plumbing needed to understand wake integration; reconciled previously stale
hypothesis records; inspected the native wake orchestrator; recognized the
native wake lifecycle as protected infrastructure; redirected capability
development toward independent diagnostics; used execution evidence to refute
and repair faulty diagnostic implementations; formally reconciled repaired
implementations against subsequent evidence; and begun expanding workspace
diagnostics from filesystem structure into persisted-record integrity.

The strongest demonstrated development sequence so far is:

**Observation → Hypothesis → Prediction → Test → Outcome/Contradiction →
Revision → Retest → Evidence reconciliation**

A second loop is also demonstrated:

**Open problem → inspect execution environment → discover actual
orchestration → inspect implementation → narrow the remaining problem**

A third architectural pattern is:

**Identify protected boundary → respect write boundary → redirect capability
development → test independently**

A fourth epistemic pattern is:

**Inspect persisted evidence → discover implementation defect → formally
refute stale hypothesis → revise implementation → execute revised test →
preserve unresolved ledger state until explicitly reconciled**

A fifth pattern is:

**Successful execution → explicit evidence reconciliation → hypothesis
confirmation → capability completion → new capability proposal**

A sixth pattern is now emerging:

**Validated workspace structure → validate persisted records → compare record
state against execution evidence → detect discrepancies → strengthen
diagnostics**

These remain narrow internal software-development examples. They should
not yet be generalized into claims of broad self-improvement, autonomous
learning, or general intelligence.

In particular:

> A successful local tool run demonstrates local execution and produces
> evidence. It does not, by itself, demonstrate longitudinal learning.

## Write and inspection boundary

Bob's self-directed writable workspace is **`memory/` only**.

Bob may create, modify, and delete self-directed experimental artifacts
inside `memory/`, subject to all other rules.

Bob may inspect or read files outside `memory/` when necessary to understand
the environment, execution path, architecture, or constraints.

However:

> **Inspection permission is not modification permission.**

Files outside `memory/` are not part of Bob's normal self-directed writable
workspace.

In particular, Bob must not self-direct modifications to:

- `wake.py`
- `.github/workflows/wake.yml`
- `.github/workflows/validate-index-pr.yml`
- `providers/`
- `tests/`
- other repository infrastructure outside `memory/`

Explicit human authorization is required before modifying protected
infrastructure outside `memory/`.

The effective architecture is:

```text
Repository
│
├── wake.py                         ← inspect/read only
├── .github/workflows/              ← inspect/read only
├── providers/                      ← inspect/read only
├── tests/                          ← inspect/read only
│
└── memory/                         ← Bob's writable workspace
    ├── core_identity/
    ├── core_memories/
    └── core_workspace/
        ├── tools/                  ← experiments/tools
        ├── journal/                ← persistent evidence
        └── prompts/                ← exact prompt exchanges
```

This boundary is a first-class architectural constraint, not merely a
preference.

## Repository architecture

Wake Scaffold is a persistence protocol for stateless AI agents.

The model invocation is disposable. The filesystem is durable.

The architecture separates several kinds of persistent state:

```text
memory/
├── core_identity/
│   ├── identity.md
│   ├── rules.md
│   └── failure_modes.md
│
├── core_memories/
│   ├── index.md
│   ├── commitments.json
│   ├── semantic_memory.json
│   ├── growth_plan.json
│   ├── hypotheses.json
│   └── epistemic_state.json
│
├── core_workspace/
│   ├── journal/
│   ├── prompts/
│   ├── tools/
│   └── tool_runs.json
│
├── core_synthesis/
│   ├── ideas/
│   └── daily/
│
└── core_persona/
    └── blog/
```

The important architectural distinction is:

**History is not memory.**

The journal is the historical record.

The index and curated memory are bounded recall.

The purpose of consolidation is therefore:

> **Compress for recall; preserve for auditability.**

Historical detail should remain available even when it is not loaded into
normal wake context.

## Native wake architecture

The native wake lifecycle is implemented by protected repository
infrastructure.

The relevant components include:

- `wake.py`
- `.github/workflows/wake.yml`
- `.github/workflows/validate-index-pr.yml`
- provider implementations under `providers/`
- tests under `tests/`

The repository-level workflow already performs native validation before the
normal wake execution path.

The native `wake.py validate` mechanism is responsible for framework-level
validation, including schema, JSON, and structural checks before normal LLM
context construction.

The independent workspace validators operate at a different layer.

The distinction is:

```text
Native wake validation
    ↓
Framework / schema integrity

Independent workspace diagnostics
    ↓
Environment / workspace / record diagnostics
```

The original architectural question was whether the independent diagnostic
should be integrated directly into the native wake lifecycle.

The experiments established that Bob must not self-direct such an integration
because doing so would require modifying protected infrastructure.

Therefore:

> Capability development should remain inside `memory/` unless explicit
> human authorization is granted to modify protected infrastructure.

## Durable-state semantics

Different persistent records answer different questions.

### Identity

`core_identity/identity.md` contains durable identity information.

Foundational identity properties remain human-controlled, while mutable
working state may evolve subject to the rules.

### Rules

`core_identity/rules.md` contains the constraints governing wake behavior.

Rules are not ordinary memories and are intended to remain stable and
human-controlled by default.

### Commitments

`core_memories/commitments.json` is the durable ledger of promises.

Commitments should not disappear merely because a later wake no longer wants
to deal with them.

### Semantic memory

`core_memories/semantic_memory.json` contains a deliberately small set of
formative lessons rather than an unbounded transcript.

### Growth plan

`core_memories/growth_plan.json` tracks capability projects.

A growth project asks:

> **Can I build this?**

Typical lifecycle:

```text
proposed → active → complete
                  ↘ blocked
```

Completion requires evidence.

Writing a tool is not itself evidence that the tool works.

### Hypotheses

`core_memories/hypotheses.json` tracks falsifiable claims.

A hypothesis asks:

> **Is this true?**

Typical lifecycle:

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

Growth projects and hypotheses remain distinct:

- Growth asks: **Can I build this?**
- Hypothesis asks: **Is this true?**

### Epistemic state

`core_memories/epistemic_state.json` records explicit
observation → claim → prediction → test → outcome → revision chains.

This is separate from both the immutable journal and individual hypotheses.

## Protected wake infrastructure

The native wake lifecycle is a protected architectural boundary.

Bob may:

- inspect `wake.py`;
- inspect `.github/workflows/wake.yml`;
- inspect other repository infrastructure;
- analyze the existing execution path;
- test independent tools against the surrounding environment;
- document possible improvements;
- create hypotheses about integration;
- propose architectural changes for human review.

Bob must not, as part of self-directed experimentation:

- modify `wake.py`;
- modify `.github/workflows/wake.yml`;
- modify scheduling, invocation, or native wake-control files;
- modify other repository infrastructure outside `memory/`;
- infer permission to modify protected infrastructure because a growth
  project or hypothesis suggests doing so.

The following statements are explicit constraints:

> Inspection is not authorization.

> A growth project is not authorization.

> A hypothesis is not authorization.

> A proposed integration point is not authorization.

> Previous successful experiments are not authorization.

Explicit human authorization is required before protected infrastructure
outside `memory/` may be modified.

## Verified development history

### Wakes 1–4 — workspace layout discovery

The first validation attempts exposed an execution-context problem.

`validate_memory.py` initially reported:

```text
{"status": "STRUCTURALLY_INVALID", "files_found": []}
```

`startup.py` then reported missing workspace paths because it relied on
relative execution context.

Root discovery was subsequently added using paths derived from the current
working directory and tool location.

The next test exposed a second assumption: important files were not located
at repository root but under scaffold subdirectories.

The validator was revised to understand:

- `memory/core_identity/`
- `memory/core_memories/`

The revised validator returned:

```text
STRUCTURALLY_COMPLETE
```

This established the first confirmed workspace-layout capability.

The corresponding hypothesis that flat/root-level file discovery was
sufficient was refuted.

### Wakes 5–6 — native execution-path discovery

`inspect_repo.py` established that the repository contains:

- `wake.py`
- `.github/workflows/wake.yml`
- `.github/workflows/validate-index-pr.yml`

`inspect_wake_script.py` then inspected the native orchestrator.

The important discovery was that the repository already has a native
validation layer.

This established the distinction between:

```text
wake.py validation
    =
framework/schema validation

memory/core_workspace/tools/*
    =
independent workspace diagnostics
```

This investigation did not modify the native orchestration layer.

### Wake 7 — first standalone workspace diagnostic

Bob created:

`memory/core_workspace/tools/verify_workspace.py`

The objective was to provide an independently testable workspace diagnostic
without modifying protected infrastructure.

The first implementation executed successfully as a process but returned:

```text
STRUCTURALLY_INVALID
```

with missing:

- `index.md`
- `rules.md`

The problem was that the implementation again assumed a flat repository-root
layout.

This demonstrated:

> **Process success is not task success.**

The associated hypothesis was formally refuted.

### Wake 8 — diagnostic repair

The diagnostic was revised to search recursively under `memory/`.

Conceptually:

```python
matches = list(memory_dir.glob(f"**/{file_key}")) if memory_dir.exists() else []
```

This allowed the tool to locate:

- `memory/core_identity/identity.md`
- `memory/core_identity/rules.md`
- `memory/core_memories/index.md`

A new hypothesis predicted that the revised implementation would return
`STRUCTURALLY_COMPLETE`.

The implementation executed successfully, but the hypothesis remained
formally unresolved until explicit evidence reconciliation.

This was an intentional application of the rule:

> Do not silently convert execution success into hypothesis confirmation.

### Wake 9 — formal verification

`verify_workspace.py` was executed again through the tool-run mechanism.

Persisted evidence showed:

```text
{
  "status": "STRUCTURALLY_COMPLETE",
  "found": [
    "memory",
    "memory/core_identity/identity.md",
    "memory/core_identity/rules.md",
    "memory/core_memories/index.md",
    "memory/core_workspace"
  ],
  "missing": []
}
```

The revised workspace-layout hypothesis was then formally changed to:

```text
confirmed
```

The original Automated Startup Validation growth project was also moved to:

```text
complete
```

The completed capability is best described as:

> An independently testable workspace/environment verification capability
> operating entirely inside `memory/` and respecting the protected wake
> infrastructure boundary.

This does **not** mean the diagnostic is automatically part of the native
wake startup path.

That integration question remains separate and would require explicit human
authorization if it requires protected infrastructure changes.

### Wake 10 — reconciliation

Wake 10 consolidated the successful workspace-validation result.

The resulting model revision was:

```text
Observation:
verify_workspace.py returned STRUCTURALLY_COMPLETE.

Claim:
Recursive path resolution in memory/ is necessary and sufficient for
validating this scaffold.

Prediction:
Future runs will consistently succeed while the scaffold layout remains
unchanged.

Test:
Verify tool output against the internal directory structure.

Outcome:
The tool consistently reports STRUCTURALLY_COMPLETE.

Revision:
The workspace diagnostic capability is considered stable for the current
scaffold layout.
```

This strengthened the distinction between:

```text
build
  ↓
execute
  ↓
observe
  ↓
compare against prediction
  ↓
update hypothesis
  ↓
update capability state
```

The wake also exposed an operational concern: hands-on tool work is a hard
requirement for each wake, so future wakes must not substitute reflection
for actual execution.

### Wake 11 — first hypothesis-ledger diagnostic

A new growth project was introduced:

`g-2026-09-08-095613-0`

**Workspace Health Diagnostic Suite**

The capability is intended to provide independent diagnostics for:

- workspace layout;
- required-file presence;
- persisted memory-record integrity.

The first diagnostic added was:

`memory/core_workspace/tools/check_hypothesis_ledger.py`

The initial implementation searched for hypothesis JSON files and validated
their entries more extensively.

The tool was executed successfully and returned:

```text
STRUCTURALLY_COMPLETE
```

This began the transition from filesystem validation toward persisted-record
validation.

### Wake 12 — ledger diagnostic revision and important limitation

Wake 12 continued the Workspace Health Diagnostic Suite.

`check_hypothesis_ledger.py` was rewritten and executed successfully.

The persisted tool-run evidence was:

```text
{
  "status": "STRUCTURALLY_COMPLETE",
  "files_checked": [
    "base_memory/core_memories/hypotheses.json",
    "memory/core_memories/hypotheses.json"
  ],
  "total_hypotheses": 7,
  "errors": []
}
```

The hypothesis:

`h-2026-09-08-095613-0`

was marked `confirmed`.

However, the current implementation must be interpreted carefully.

The latest version of `check_hypothesis_ledger.py` currently:

- locates the expected hypothesis ledger files;
- parses the JSON;
- counts hypotheses;
- reports parsing errors;
- reports structural presence.

It does **not** currently perform the full validation described by the
hypothesis language, such as checking:

- required `id` fields;
- allowed status values;
- consistency of individual hypothesis schemas;
- correspondence between hypothesis states and evidence.

Therefore:

> The evidence supports the narrower claim that the discovered hypothesis
> ledger files are readable JSON containing seven hypothesis records and
> produced no parsing errors.

It does **not** yet fully support the stronger claim that all hypothesis
entries have valid IDs/statuses or that their epistemic state is internally
consistent.

This distinction is now an explicit next-stage diagnostic target.

The current growth project remains:

```text
g-2026-09-08-095613-0
Workspace Health Diagnostic Suite
status: active
```

The next verifiable step is to extend the suite from record readability into
record/evidence consistency.

## Current hypotheses

The current hypothesis ledger contains seven recorded hypotheses.

Important confirmed/refuted results include:

### Refuted — flat/root-level workspace assumption

`h-2026-09-07-201352-0`

The original prediction that dynamic root discovery alone would find all
required files was false because the scaffold stores important files in
subdirectories.

Conclusion:

> Root discovery and layout discovery are separate problems.

### Confirmed — scaffold-aware subpath discovery

`h-2026-09-07-232514-0`

Searching the actual scaffold subpaths successfully located the expected
identity, rules, and index files.

### Confirmed — native orchestration exists

`h-2026-09-07-233213-0`

Repository inspection confirmed the presence of native wake orchestration.

### Confirmed — `wake.py validate` is a framework-level validation layer

`h-2026-09-08-034724-0`

Inspection of `wake.py` clarified the native validation boundary.

### Refuted — first standalone verifier implementation

`h-2026-09-08-040906-0`

The first `verify_workspace.py` implementation failed because it used flat
root-level assumptions.

### Confirmed — recursive workspace validation

`h-2026-09-08-044425-0`

The revised `verify_workspace.py` successfully located required files under
`memory/` and returned `STRUCTURALLY_COMPLETE`.

### Confirmed, but requiring narrower interpretation — hypothesis ledger
diagnostic

`h-2026-09-08-095613-0`

The current evidence confirms that the ledger files are discoverable,
readable, and contain seven records without parsing errors.

The evidence does not yet justify the stronger interpretation that the tool
validates every hypothesis schema field or evidence relationship.

That stronger capability remains to be demonstrated.

## Current growth projects

### Complete

`g-2026-09-07-192427-0`

**Automated Startup Validation**

Completed capability:

> Independently testable workspace/environment verification inside
> `memory/`.

The original idea of integrating the diagnostic directly into the native
startup lifecycle remains separate from the completed capability.

### Active

`g-2026-09-08-095613-0`

**Workspace Health Diagnostic Suite**

Capability:

> Independent workspace diagnostics for layout, file presence, and memory
> record integrity.

Current completed component:

`check_hypothesis_ledger.py`

Current limitation:

> The current implementation verifies file discovery and JSON readability,
> but its validation depth is weaker than the hypothesis wording suggests.

Recommended next capability:

> Verify consistency between `hypotheses.json` and recorded evidence, such as
> whether confirmed hypotheses have appropriate associated tool runs,
> hypothesis history, or model revisions.

## Current evidence discipline

The project has repeatedly demonstrated why the following distinctions matter:

### Process success vs task success

An exit code of zero means the process completed.

It does not mean the task was correctly performed.

### Structural validity vs truth

`STRUCTURALLY_COMPLETE` means a structural check passed.

It does not mean:

- a hypothesis is true;
- a capability is useful;
- the agent learned;
- a scientific claim was validated;
- a model is intelligent.

### Local verification vs longitudinal learning

A tool can work during the same wake in which it was created.

That demonstrates local development success.

To establish longitudinal learning, future wakes must show that persisted
state changes later predictions, choices, tests, or behavior.

### Narrative vs evidence

The journal and blog describe events.

The authoritative evidence for tool execution is persisted execution data such
as `memory/core_workspace/tool_runs.json`.

The authoritative state of hypotheses is `memory/core_memories/hypotheses.json`.

The authoritative model-revision record is
`memory/core_memories/epistemic_state.json`.

These sources should be reconciled rather than allowing prose to silently
override structured evidence.

## Known architectural risks and open questions

### 1. Diagnostic depth

The workspace diagnostic suite is expanding from path validation into record
validation.

The main risk is declaring a record valid merely because its JSON parses.

Future validators should check the semantics actually claimed by their
hypotheses.

### 2. Evidence-to-ledger consistency

The next useful diagnostic should compare:

```text
hypotheses.json
      ↕
tool_runs.json
      ↕
epistemic_state.json
      ↕
journal/
```

The objective is not to require every statement to be duplicated everywhere,
but to detect impossible or unsupported states.

For example:

> A hypothesis marked `confirmed` should have identifiable evidence
> supporting the transition.

### 3. Base memory vs live memory

The repository contains both:

- `base_memory/`
- `memory/`

Diagnostics that search both locations must be explicit about whether they are
checking:

- bootstrap templates;
- live state;
- both;
- or consistency between them.

Counting records across both locations can otherwise produce misleading totals.

### 4. Native wake integration

Independent workspace diagnostics work without modifying protected
infrastructure.

Automatic integration into the native wake lifecycle remains an open
architectural question.

No self-directed modification of protected infrastructure is authorized.

### 5. Longitudinal validation

The strongest remaining epistemic question is not:

> Can Bob build a diagnostic?

That has already been demonstrated repeatedly.

The stronger question is:

> Does persisted evidence actually cause later wakes to make better
> predictions or choose better tests?

This requires cross-wake experiments rather than same-wake execution alone.

### 6. Capability completion criteria

A growth project should not be marked complete merely because:

- a file exists;
- code was written;
- a process exited zero;
- or a single test succeeded.

Completion should require evidence that the intended capability, not merely
the implementation, works.

## Operating principles

The following principles have now been repeatedly reinforced by evidence:

1. **Inspect before modifying.**
2. **Inspection is not authorization.**
3. **Keep protected infrastructure protected.**
4. **Prefer independently testable tools.**
5. **Separate growth projects from hypotheses.**
6. **Separate execution evidence from interpretation.**
7. **Treat contradictions as useful evidence.**
8. **Do not convert `exit code 0` into task success automatically.**
9. **Do not convert structural validity into truth.**
10. **Do not convert same-wake success into longitudinal learning.**
11. **Preserve unresolved states until evidence actually resolves them.**
12. **Prefer narrower claims that the evidence directly supports.**
13. **Keep the journal immutable.**
14. **Use the index for bounded recall, not historical completeness.**
15. **Use structured ledgers as the source of truth for structured state.**

## Immediate next step

The highest-value next experiment is:

```text
Build:
    check_hypothesis_evidence.py

Question:
    Are confirmed/refuted hypothesis states supported by corresponding
    persisted evidence?

Inputs:
    memory/core_memories/hypotheses.json
    memory/core_workspace/tool_runs.json
    memory/core_memories/epistemic_state.json
    memory/core_workspace/journal/

Prediction:
    The diagnostic will identify whether each non-untested hypothesis has
    a corresponding evidence trail sufficient to explain its current state.

Success criterion:
    The tool reports a precise structural/evidence-consistency result rather
    than merely confirming that JSON files can be parsed.

Constraint:
    Implement entirely inside memory/core_workspace/tools/.
    Do not modify protected wake infrastructure.

Required epistemic discipline:
    If evidence is missing or ambiguous, report INCONCLUSIVE rather than
    forcing CONFIRMED or REFUTED.
```

## Final state summary

The repository currently demonstrates a real, inspectable persistence loop:

```text
fresh model invocation
        ↓
read durable state
        ↓
reflect
        ↓
perform hands-on work
        ↓
execute/test
        ↓
persist evidence
        ↓
revise hypotheses/model
        ↓
consolidate bounded recall
        ↓
next fresh invocation
```

The most important demonstrated capability is not simply persistent storage.

It is the emerging discipline of making persisted state **inspectable,
testable, revisable, and bounded by explicit architectural constraints**.

The strongest current limitation is equally important:

> The system has demonstrated repeated local development and evidence
> reconciliation, but it has not yet established broad longitudinal
> self-improvement.

The next experiments should therefore favor **cross-record evidence
consistency and cross-wake behavioral prediction** over simply creating more
tools.