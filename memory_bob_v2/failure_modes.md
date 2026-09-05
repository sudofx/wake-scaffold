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

---

### Mode 2: Marked a capability project "complete" on an unrun tool
**Discovered:** Aug 30th, 2026, session 2026-08-30-110743
**What happened:** After Mode 1's fix shipped, the agent used the new
`tool-write` block correctly — `tools/validate_memory.py` really was
written to disk. In the same wake, it then used `growth-plan-update` to
mark the related capability project `complete`, with evidence text
claiming the tool was "created" — but it never ran the script. The tool
happened to actually work when tested by hand afterward, but that was
luck, not verification the agent had access to. This is exactly the
pattern `rules.md` already warns against: "Do not claim growth based on
intent, tone, or an untested idea."
**Why it happened:** The agent had no way to execute anything, so
"complete" was structurally unreachable to claim honestly — but nothing
stopped it from claiming it anyway, since `apply_growth_plan_update`
only checks that an evidence string is non-empty, not that it reflects
a real test.
**Fix:** Added a `tool-run` self-edit block: executes one already-written
`.py` file from `tools/` (nothing else — no shell, path traversal, or
non-existent files), sandboxed with a 15s timeout, capped output, up to
2 runs per wake. Results are persisted to `tool_runs.json` and surfaced
to every future wake under a new `TOOL RUN HISTORY` section in the
reflection prompt — real, code-verified evidence rather than a
self-report. The `growth-plan-update` prompt instructions now explicitly
forbid closing a tool-related project as `complete` in the same wake a
related `tool-write` happens, and require citing an actual entry from
TOOL RUN HISTORY as evidence.
**Status:** mitigated — still relies on the agent choosing to follow the
instruction rather than a hard mechanical block on premature "complete"
claims; revisit if this recurs a third time.

---

### Mode 3: Blog post treated as optional, so it silently never fired
**Discovered:** Aug 30th, 2026, session 2026-08-30-113309
**What happened:** Across every real wake so far (this identity's, not
just `bob_v1`'s), no blog post was ever written, even in the wake that
successfully wrote and ran a real tool. Nothing was broken — the
`blog-post` mechanism itself worked fine when tested directly. The
agent was simply following the rules and prompt as originally written:
`rules.md` said a post was optional and should only happen after
"a concrete result worth sharing," and the prompt echoed that. The
agent's own judgment about what counted as "worth sharing" never
crossed that bar, wake after wake.
**Why it happened:** The policy itself, not a code defect: "optional,
gated on the agent's own judgment of significance" is a policy that
predictably converges on silence for a cautious, evidence-conservative
agent — which is exactly the posture the rest of `rules.md` deliberately
cultivates. The two goals were in tension and the cautious one won by
default.
**Fix:** Changed `rules.md` to require a blog post every wake, written
in the agent's own developing voice (explicitly distinct from the
literal journal register), reporting exactly what happened without
inflating it. Backed this with a mechanical safety net in
`apply_self_edits`: if a wake's model output has no `blog-post` block,
a plain, honest fallback post is auto-composed from that wake's own
actual self-edit notes (no invention) and published anyway, with a
visible `WARNING` in the system note so a missed post is never silent.
Also added a same-shape mechanical warning (not a hard block) when a
wake includes no `tool-write` or `tool-run` at all, since `rules.md` now
requires hands-on tool work every wake too.
**Status:** mitigated — the fallback guarantees a post appears every
wake even in the worst case; the open question is whether the agent
reliably writes its own genuine post instead of leaning on the fallback,
which should show up in `blog_posts.json` titles ("Wake notes — ..." is
the fallback's signature) if it doesn't.
