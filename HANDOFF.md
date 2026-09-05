# Handoff: theater-audit fixes (2026-09-05)

Context: Rob asked for an audit of whether Bob's tools in `memory/tools/`
are real or theater. Findings and fixes below are code-review edits made
directly to the repo (not a wake cycle) — journal/hypotheses/growth_plan
were left untouched per the append-only rule.

## What was found
1. `concept_evaluator.py` / `quantum_batch_evaluator.py` labeled a plain
   length/keyword heuristic "VALID_SCIENTIFIC_FRAMEWORK" — the tools
   worked correctly, but the label overclaimed what a premise/prediction
   count can actually tell you.
2. `mind_map_organizer.py` used `shutil.copy2()` to physically duplicate
   every tool file into `core_functions/`, `core_thinking/`,
   `core_evaluators/`, `core_maintenance/` — real code, but each
   "organize" run was disk-duplication logged as growth, not a new
   capability.
3. Blog posts narrate small fixes in reflective prose — not fixed here,
   this is a style/incentive issue rather than a bug; see rules.md
   change below for the closest lever available.

## What changed
- `memory/tools/concept_evaluator.py`: renamed status labels
  (`VALID_SCIENTIFIC_FRAMEWORK` → `STRUCTURALLY_COMPLETE`,
  `NEEDS_REFINEMENT` → `INCOMPLETE_STRUCTURE`), added a `note` field
  naming the actual mechanism. Verified by running it (see below).
- `memory/tools/quantum_batch_evaluator.py`: same relabeling
  (`VALID_SCIENTIFIC_FRAMEWORK` → `STRUCTURALLY_COMPLETE`), added `note`.
- `memory/tools/mind_map_organizer.py`: rewritten to stop copying files;
  it now only ever writes `mind_map.json` (a category manifest pointing
  at the single canonical copy of each tool). Ran it — confirmed no new
  subdirectories or duplicate files are created.
- Deleted `memory/tools/core_evaluators/`, `core_functions/`,
  `core_maintenance/`, `core_thinking/` — these held only duplicate
  copies with no functional difference from the canonical files.
- `memory/rules.md` and `base_memory/rules.md`: added a new "Tool
  honesty" section requiring (a) status labels describe the actual
  check performed, not the claim's truth, (b) reorganizing/copying
  existing tools doesn't count as a new capability in growth_plan.json,
  (c) checking for an existing tool doing the same check before writing
  a new one under a new name.

## Verified
- `python3 concept_evaluator.py` and `python3 quantum_batch_evaluator.py
  carnegie_concept.json` both run clean, new labels present.
- `python3 mind_map_organizer.py organize` runs clean, writes only
  `mind_map.json`, creates no subdirectories.
- Full suite: `python3 -m pytest tests/test_wake.py -q` → 39 passed.
- Confirmed nothing in `wake.py`, `tests/test_wake.py`, or `config.yaml`
  referenced the deleted subdirectories before removing them.

## Not fixed (needs your call, not a code fix)
- Blog-post narrative-to-substance ratio. Rules.md already has a
  "Genuine curiosity vs. performance" section that's fairly strong;
  I didn't find a clean way to tighten it further without risking the
  Gen-X voice/stakes requirement you also asked for. If this keeps
  showing up, the next lever is probably a stated cap (e.g. "blog post
  must name the one concrete artifact/result before any reflection")
  rather than more prose in rules.md.

---

# Handoff addendum: identity reset (2026-09-05, same session)

Ran the archive/reset via the real `wake.py` CLI (not hand-rolled file
moves), so `IDENTITIES.md`, blog rendering, and index.md self-links all
updated the way they're designed to:

```
python3 wake.py reset --archive-as bob_v2 --name Bob --purpose "..."
```

## What this did
- **Archived** the old Bob (88 journal entries, all tools, blog history,
  full growth_plan/hypotheses) to `memory_bob_v2/`. Nothing in it was
  edited — it's a straight `shutil.move`, exactly per `archive_current_
  identity()`'s contract. `IDENTITIES.md` row updated to `archived`.
- **Bootstrapped** a fresh `memory/` for a new Bob from `base_memory/`,
  via `bootstrap_identity()`. New Bob starts with:
  - Empty `growth_plan.json`, `hypotheses.json`, `core_memories.json`,
    `commitments.json` — no `tools/` directory. It earns all of this
    itself, same as any new identity. I did **not** carry forward old
    Bob's actual hypotheses or growth-plan history; carrying forward
    *conclusions without the agent re-deriving them* would violate the
    project's own evidence-based-growth principle.
  - A condensed **Purpose** (set via `--purpose`) that keeps the
    original spirit — curious, evidence-first, builds real tools — but
    drops the hard anchor to two specific books that drove the old
    identity's thematic rut, and explicitly names the anti-narrowing
    and label-honesty lessons.
  - A **Known limitations** entry in `identity.md` and two **Mode**
    entries in `failure_modes.md`, both explicitly marked as inherited
    from the archived predecessor (not self-observed yet), condensed
    from the real audit findings: thematic narrowing once an evaluator
    tool exists, and duplicate-tool/inflated-label churn logged as
    growth. Framed as a *hypothesis to test against its own behavior*,
    not a settled fact about the new identity — consistent with
    `rules.md`'s "never claim certainty about something not verifiable
    from the files in memory/."

## Where this was baked in
`base_memory/identity.md` and `base_memory/failure_modes.md` were
edited directly (not just `memory/`), so this condensed history will
also seed any *future* `new`/`reset` call, not just this one Bob. If
you want the inherited-limitations text to be Bob-specific rather than
the default for any future identity spun up from this template, say so
and I'll move it out of `base_memory/` and into a one-time patch of
`memory/identity.md` and `memory/failure_modes.md` instead.

## Verified
- `IDENTITIES.md` shows old Bob as `archived` -> `memory_bob_v2/` and
  new Bob as `active` -> `memory/`.
- `memory_bob_v2/` has all 88 journal entries and all tools intact,
  untouched.
- New `memory/` has zero journal entries, empty growth_plan/hypotheses/
  core_memories/commitments, no `tools/` dir, and the condensed
  identity.md/failure_modes.md described above.
- Full suite: `python3 -m pytest tests/test_wake.py -q` -> 39 passed.
