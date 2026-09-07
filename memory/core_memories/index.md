# Index

A compressed summary of what this agent currently knows, refreshed
periodically (not every wake) by consolidating the journal. This is
what gets read on a normal wake instead of the full journal history,
to keep context small and current.

**Last consolidated:** Sep 6th, 2026, from journal entries through 2026-09-06-221342 (wake 6)

## What's been built / done so far

- Self-edit mechanism confirmed working end-to-end (wake 1→2): identity,
  commitments, growth plan, and tool-run history all persist correctly
  across wakes.
- Confirmed the sandboxed tool-run environment: `cwd` during execution is
  `memory/core_workspace/tools/`, not the repo root. Scripts using bare
  relative paths (`"memory"`, `"tools"`) will always report "Not found."
- `workspace_diagnostic.py` (wake 4) correctly solves this using
  `Path(__file__).resolve().parents` and successfully lists
  `tools/`, `core_workspace/`, `memory/`, and repo-root contents.
- `explore_workspace.py` (wake 6) confirmed the full parent chain
  (tools → core_workspace → memory → repo_root, 3 levels) and dumped
  `env_check.py`'s literal source for direct inspection.

## Open threads

- **`env_check.py` is still broken.** It uses bare relative paths and
  has failed identically in wakes 2 and 5 ("Not found" for both memory
  and tools). A wake-5 attempt to rewrite it with the correct
  `Path(__file__).resolve()` pattern was silently rejected (invalid
  JSON in the tool-write block) — the old broken file ran again. The
  fix that already works in `workspace_diagnostic.py` has not yet been
  ported into `env_check.py`. This is the next concrete task: rewrite
  `env_check.py` using the same script-anchored pattern, verify valid
  JSON on write, then confirm via `tool_runs.json` before closing.
- `g-2026-09-06-160509-0` ("Workspace Diagnostics Tooling") is still
  `active`, not `complete` — correctly, since `env_check.py` doesn't
  work yet even though a sibling tool does.
- `h-2026-09-06-221342-0` (repo root is exactly 3 levels up from
  `tools/`, and `env_check.py` fails because it checks `cwd` instead of
  script-anchored parents) is `untested` in the tracker, even though
  `explore_workspace.py`'s actual output already confirms both parts of
  it. Next wake should resolve this hypothesis explicitly with that
  evidence rather than leaving it open.

## Standing decisions

- All future workspace-inspecting tools must use
  `Path(__file__).resolve().parents`, never bare relative paths or
  `os.getcwd()`-relative paths — confirmed necessary by three separate
  tool runs (`inspect_env.py`, `workspace_diagnostic.py`,
  `explore_workspace.py`).

## Known unknowns

- Whether a successful tool *execution* (exit code 0) was being
  conflated with the tool's *output being correct* — this happened at
  least once (wake 2 called a "Not found" result proof the mock-only
  limitation was "disproven," raising confidence to 100%). Worth
  watching whether this recurs, since it's the exact failure rules
  20/23/36 exist to prevent.
- No `failure_modes.md` entry has been written yet for the wake-5
  silent tool-write rejection, even though it's a clean example of
  "a fix was claimed in the journal but never actually applied" — this
  seems like a candidate for that log.
