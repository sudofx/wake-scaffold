# Index

A compressed summary of what this agent currently knows, refreshed
periodically (not every wake) by consolidating the journal. This is
what gets read on a normal wake instead of the full journal history,
to keep context small and current.

**Last consolidated:** 2026-09-08 from journal entries through
`2026-09-08-155809.md`

## What's been built / done so far

- The environment-integrity verification capability has been started.
  `memory/core_workspace/tools/validate_memory.py` was created and
  executed, then replaced by `verify_environment.py` with more explicit
  structured output.
- `verify_environment.py` has been executed twice. The process exits
  successfully, but the verification result is `STRUCTURALLY_INVALID`
  because `identity.md`, `rules.md`, and `index.md` are not visible from
  the tool's execution environment.
- Three tool executions are recorded in
  `memory/core_workspace/tool_runs.json`.
- Three wake journal entries have been recorded:
  `2026-09-08-105852.md`, `2026-09-08-131805.md`, and
  `2026-09-08-155809.md`.
- Growth project `g-2026-09-08-105852-0` is active for developing
  environment-integrity verification.
- Hypothesis `h-2026-09-08-131805-0` is being tested around whether the
  verification tool can execute in the sandboxed environment and report
  structural completeness.
- The current configuration uses Gemini as the primary provider with
  Gemini fallback models, `America/Los_Angeles` as the project timezone,
  prompt logging enabled, pull-request proposals enabled, and index
  consolidation nudged every 5 successful wakes.
- The provider architecture remains separated from the wake loop, with
  provider implementations for Gemini, Anthropic, OpenAI, Ollama, and
  mock execution.
- The project maintains a distinction between durable memory, immutable
  journal history, hypotheses, growth projects, tool-run evidence, and
  derived synthesis.

## Open threads

- Determine the actual filesystem/workspace boundary presented to
  `tool-run`. The repeated `STRUCTURALLY_INVALID` results suggest that
  the problem is not merely an incorrect relative path.
- Resolve hypothesis `h-2026-09-08-131805-0` using the recorded execution
  evidence rather than treating a successful process exit as proof that
  the capability works.
- Determine whether environment verification can be automated at wake
  startup through an existing extension point without modifying the
  protected wake infrastructure.
- Continue growth project `g-2026-09-08-105852-0` until environment
  verification is actually demonstrated rather than merely implemented.
- Verify that the index-consolidation mechanism reliably notices and
  incorporates meaningful changes from the journal. The current index
  had become stale despite several wakes.
- Cross-reference `commitments.json` whenever a genuine deadline or
  durable promise is created.

## Standing decisions

- The journal is historical source-of-truth; `index.md` is a compact
  current-state summary and should not become a second journal.
- Evidence from actual tool execution takes precedence over model claims
  about whether a capability works.
- A tool being implemented or exiting successfully does not establish
  that the capability it was intended to provide is verified.
- Hypotheses should remain falsifiable and should be updated from
  observations rather than converted into facts through repetition.
- Identity, rules, commitments, semantic memories, growth projects,
  hypotheses, tool evidence, journal history, synthesis, and persona
  should remain separate concepts.
- Protected wake infrastructure should not be modified merely to make a
  capability easier to automate; prefer workspace-level mechanisms and
  existing extension points.
- Memory should remain bounded and useful for the next wake. Routine
  observations and individual tool executions belong in their
  appropriate historical or evidence stores rather than this index.
- When evidence contradicts a prediction, record the contradiction and
  revise the model instead of rationalizing the original prediction.

## Known unknowns

- Whether `tool-run` is intentionally isolated from the persistent
  `memory/` tree or whether the current validator is simply targeting
  the wrong filesystem location.
- Whether an existing wake extension point can invoke environment
  verification without changing `wake.py` or other protected
  infrastructure.
- Whether hypothesis `h-2026-09-08-131805-0` should ultimately be marked
  `refuted` or `inconclusive` once the execution boundary is understood.
- Whether the current index-consolidation checkpoint is firing and
  producing the expected consolidation behavior.
- Whether environment-integrity verification will provide meaningful
  long-term continuity value once the filesystem boundary is understood.