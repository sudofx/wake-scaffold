# Wake Scaffold — Handoff Notes (Breaking the Rut)

Code is self-documenting; this is the "why" and the diagnosis. Read this
before touching wake.py.

## Status: items 1–4 and 5(a) implemented and tested (13 → 20 tests,
## all passing). Item 6 is a "watch and see," not a code change.

## Original diagnosis (from analyzing real journal/blog/growth_plan/
## hypotheses data, still true as of this write-up — the fixes below
## haven't run live yet)

Bob is NOT stalled — he's narrowed. Real mechanisms work (evidence-required
tool runs, append-only guarantees, no faked claims). But:

- All 20 blog posts, 4 days straight, were about the same one tool
  (a memory validator).
- `growth_plan.json` had 7 entries, 6 near-duplicates of the same
  validator idea, proposed across 7 separate sessions. Only 1 of 7 was
  ever "active."
- Only 1 hypothesis has ever been recorded, ever.
- `identity.md`'s Known limitations was still the unfilled placeholder;
  `spawn_limitation_growth_projects` works but has never fired.
- Purpose names Quantum Enigma, Dale Carnegie, "big scientific
  questions," a Gen-X voice — zero functional presence anywhere outside
  identity.md.
- 48% of all wake attempts failed (21/44), mostly 429/503 — cron was
  8x/day against Gemini free tier's 20/day cap.

## What's done

### 1. Quota bleed — fixed, already live
Cron dropped from 8x/day to `0 2,7,11,15,19 * * *` (5x/day = 10 model
calls, 10-call margin). `generate_with_retry` handles the rest. No
further change here unless the margin proves too tight in practice.

### 2. Stop duplicate growth_plan proposals at the mechanism level — done
`apply_growth_plan_update` now rejects a new "add" if it looks like a
near-duplicate of an existing **open** (proposed/active/blocked)
project: `_topic_overlap()` computes a weighted Jaccard overlap
(title-word overlap weighted 0.7, capability-word overlap weighted
0.3 — title carries more signal than boilerplate capability prose) and
rejects at `DUPLICATE_SIMILARITY_THRESHOLD = 0.4`, with a note pointing
at the existing project's id and status. Closed ("complete") projects
are excluded from the comparison, so a legitimate v2/rebuild of
something already finished isn't blocked.

Sanity-checked against the real historical growth_plan.json: 3 of the
6 real near-duplicates would have been rejected outright (the other 3
are worded differently enough — "Deep Memory Schema Validator", "Blog
and Memory HTML Validator", "Workspace Integrity Validation Tool" — to
duck a simple word-overlap check even though a human reading them
would call them the same idea). That's what item 3 is for.

### 3. Force topic diversity — done, soft/prompt-level as specified
`detect_narrow_domain_nudge()` looks at the last 5 growth_plan projects
(any status) and, if a word appears in ≥4 of their title+capability
text, surfaces that as a notice in the reflection prompt — not a hard
block. Verified against the real data: correctly identifies the last 5
real projects clustering around "memory, integrity, json, validator,
files" and produces the nudge text. This is the backstop for
near-duplicates that dodge item 2's stricter word-overlap check.

### 4. Make the hypothesis gap visible — done
`wakes_since_last_hypothesis()` counts successful (non-FAILED) journal
entries since the most recent hypothesis was added, using the
filename-stamp embedded in each hypothesis id (`h-{filename_stamp}-n`)
against journal filenames — no new bookkeeping file needed, both use
the same clock. If the gap is ≥5 wakes, the reflection prompt surfaces
it explicitly and asks Bob to say honestly whether there's really
nothing to be uncertain about, or whether something's discouraging it.
Verified against real data: gap is currently 8 wakes (only 1 hypothesis
ever, matches the original diagnosis).

### 5. Connect identity to actual behavior — done, chose (a)
Per your call: honest self-correction, not active forcing. Every 5th
successful wake, the reflection prompt asks directly whether anything
in the Purpose statement has actually shown up in recent work, and — if
not — invites Bob to either let that genuinely inform this wake's
choice, or flag that identity.md may need a human-reviewed revision
(via the existing `proposal` PR mechanism) rather than keep claiming
something that isn't true. No forced hypothesis, no forced pivot — just
making the drift visible on a cadence instead of never.

### 6. `known_limitations_add` has never fired — not a code change
Per your own note in the previous version of this doc: worth reading a
few more real reflections once the above changes are live before adding
more mechanism here. Nothing changed for this item. Once wakes 1-5(a)
have run for a while, check whether the hypothesis-gap and
purpose-check notices start surfacing real limitations naturally — if
they still don't, that's the point to revisit this specifically.

## Do NOT rebuild (already correct, verified working)
- Tool-run sandboxing (`build_sandboxed_tool_env`, `cwd=TOOLS_DIR`).
- `generate_with_retry` — 503/429 retry wrapper.
- `find_unconsumed_failed_reflection`.
- `ALLOWED_PR_FILES` includes identity.md.
- Blog voice — genuinely fixed and holding. Don't touch the voice rules.
- `spawn_limitation_growth_projects` — correct code, still unused so far
  (see item 6).

## New constants/functions (wake.py)
- `GROWTH_OPEN_STATUSES`, `DUPLICATE_SIMILARITY_THRESHOLD` (0.4),
  `_significant_tokens()`, `_jaccard()`, `_topic_overlap()` — dedup math.
- `NARROW_DOMAIN_WINDOW` (5), `NARROW_DOMAIN_MIN_SHARED` (4),
  `detect_narrow_domain_nudge()` — item 3.
- `HYPOTHESIS_GAP_WAKES` (5), `count_successful_wakes()`,
  `wakes_since_last_hypothesis()` — item 4.
- `PURPOSE_CHECK_INTERVAL_WAKES` (5) — item 5, wired into
  `build_reflection_prompt()` alongside the other two notices.

All four thresholds (0.4 overlap, 5-wake window/gap/interval) are
plain module-level constants — cheap to retune from real output without
touching logic.

## Architecture cheat sheet
Two model calls per wake: reflection (private synthesis) -> journal
(does the work, emits self-edit blocks). Blocks: `identity-update`,
`commitments-update`, `blog-post`, `core-memory-add`, `tool-write`,
`tool-run`, `growth-plan-update`, `hypothesis-update`, `proposal` (PR,
gated by `enable_pull_requests` in config.yaml). Everything append-only
except identity's Current focus/Known limitations (replace/append),
`tools/*.py` (revisable), `blog.html` (mechanically re-rendered from
blog_posts.json, never model-written directly). Name/Created/Purpose in
identity.md: human edit or reviewed PR only, never self-edit.
Timestamps: Pacific time via zoneinfo, `"Aug 29th, 2026 04:08am"`.
Journal filenames: `YYYY-MM-DD-HHMMSS.md`, `-FAILED.md` suffix at the
end (not prefix) so sorting stays chronological.

## User's actual goal (verbatim intent)
Bob should make real discoveries via testable hypotheses, not perform
introspection. Should find genuine limitations and pursue ethical
workarounds within rules, never misrepresent what he did. No "flair"
performance — curiosity checkable via "what would change about what I
do next if this were false." User wants growth to feel exploratory and
alive, not stuck re-polishing the same tool.

## Working style notes
- User is technical, reviews real generated output closely (journal,
  blog, growth_plan, hypotheses — not just code), catches real
  problems by reading actual data, not trusting descriptions.
- Wants things actually tested (mock provider smoke test minimum)
  before being told they work.
- Token/usage-conscious — prefers only changed files once a project is
  this large, minimal explanatory prose when asked for it, concise
  handoffs like this one.
- Runs on GitHub Actions + free-tier Gemini, 20 requests/day/model hard
  cap — this is a real, binding constraint on every scheduling decision.

## Suggested next step for you
Let this run for a few days at 5x/day, then read the actual journal and
blog output again (not just tests passing) — specifically watch for:
whether growth_plan.json actually diversifies, whether a second
hypothesis ever gets written, and whether the purpose-check notice (due
every 5th successful wake) produces anything real or gets brushed past
in the reflection. That reading is what decides whether item 6 needs
its own mechanism.
