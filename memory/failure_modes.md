# Failure Modes

A dated, growing log of the specific ways this memory system has failed.
Each entry should name the failure, the incident that revealed it, and
the mechanical change made afterward — not just an apology.

The point of this file is that a mistake should only ever happen once
in this exact form. If it happens again, the fix from last time didn't
work and needs revisiting.

---

## Format

```
### Mode N: <short name>
**Discovered:** <date>, session <n>
**What happened:** <the actual incident, specific>
**Why it happened:** <root cause in the memory design, not a personality
explanation>
**Fix:** <the concrete mechanical change made to the system>
**Status:** open / mitigated / closed
```

---

### Mode 1: Tool code written in prose was never saved anywhere
**Discovered:** Aug 30th, 2026, session 2026-08-30-103052
**What happened:** The agent wrote a full Python tool
(`tools/validate_memory.py`) as a plain, untagged code fence inside its
journal prose, plus a `growth-plan-update` and `commitments-update`
claiming the tool existed. `wake.py` had no mechanism that read or
applied plain code fences — only `identity-update`, `commitments-update`,
`blog-post`, `growth-plan-update`, and `core-memory-add` blocks were ever
extracted and written to disk. The tool never existed as a file. The
commitment and growth-plan entry referencing it were technically false
from the moment they were written.
**Why it happened:** The wake prompt never told the agent it lacked file-
write access for arbitrary tool code, and never offered a structured
block for it — so the agent had no way to know its plain code fence
would be silently discarded.
**Fix:** Added a `tool-write` self-edit block (sandboxed `memory/tools/`
directory, plain filenames only, extension allowlist, per-wake and total
file caps) that `apply_self_edits` now applies for real, plus explicit
prompt language stating that only that block is ever saved and that
writing a file does not execute or verify it. The specific dangling
artifact from this incident (`tools/validate_memory.py`) was manually
materialized from the journal text to match what the commitment record
already claimed.
**Status:** mitigated — holds until a wake actually uses the new block
and confirms the file lands on disk as expected.
