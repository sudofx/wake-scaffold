# Index

A compressed summary of durable state. This file is intentionally
identity-neutral: a newly bootstrapped identity should not inherit
historical claims from the scaffold author's development history.

## Standing architecture facts

- Core identity lives under `core_identity/`.
- Durable memories live under `core_memories/`.
- Workspace, tools, prompts, journal, and tool evidence live under
  `core_workspace/`.
- The machine-readable `core_manifest.json` declares the active layout.
- `tool_runs.json` is the mechanical record of tool execution; a process
  exit code alone does not prove that a capability succeeded.
- Hypotheses require evidence for resolution. Growth projects are plans,
  not evidence.
- Journal entries are append-only historical records; this index is a
  derived current-state summary.

## Current state

No identity-specific history has been established yet.

## Open threads

- Establish the first useful capability project.
- Produce mechanical evidence for any capability claimed as working.
- Keep derived summaries synchronized with the underlying evidence.
