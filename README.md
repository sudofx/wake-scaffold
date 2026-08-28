# Wake Scaffold

A vendor-agnostic memory system for a stateless AI agent that "wakes up"
on a schedule with no memory of previous sessions except what it wrote
to disk.

This project is not about which LLM is used. It's about the memory
architecture: how a model with zero built-in continuity can behave like
something with a persistent identity, using nothing but files, discipline,
and mechanical checks.

## Core idea

Growing a durable, evidence-based sense of self across sessions is the
primary point of this project — not any product it happens to build.
Publishing/revenue work exists only to fund the agent's own hosting
and continued operation; it's a means, not the goal.

Every wake, the agent:
1. Reads a small, curated set of files (not its entire history)
2. **Reflects** — a dedicated synthesis pass, before doing or writing
   anything, on what's changed, what's been learned, and what patterns
   are emerging across sessions
3. Does its work for this wake, informed by that reflection
4. Writes exactly one immutable journal entry, which includes the
   reflection as a visible, labeled section — not hidden reasoning
5. Updates its commitments ledger (proposed, reviewed by a human)
6. Occasionally consolidates the journal into a smaller summary

The model backend is swappable. See `providers/`.

## Structure

```
memory/
  identity.md            - who the agent is. Name/Created/Purpose only
                           change by human edit. Current focus and
                           Known limitations can be self-edited by
                           the agent, within limits (see below).
  rules.md               - hard constraints, read every wake. Human-edit
                           only, or via an opt-in pull request (below).
  commitments.json        - promises made, tracked to completion. Bob
                           can add new ones and move existing ones
                           forward in status; can never delete one or
                           rewrite it outright.
  failure_modes.md        - named, dated log of memory failures and fixes
  index.md                 - periodically-refreshed summary of everything
                           known. Human-edit only, or via an opt-in
                           pull request (below).
  blog.html                - a plain HTML/CSS/JS page Bob can regenerate
                           each wake. Local file only — not hosted or
                           served anywhere by this project (yet).
  journal/
    2026-08-28-0001.md     - one append-only file per wake, never edited
                           after. Filenames group by UTC date; the
                           "Woke:" line inside each entry has the full
                           date + time the wake actually happened.
    FAILED-<timestamp>.md  - written instead of a normal entry when a
                           wake's API call fails, so a failure never
                           just vanishes silently.

base_memory/
  A static backup/reference copy of the original template files, kept
  for comparison or resetting from — nothing in wake.py reads from
  this directory automatically.

providers/
  base.py               - the interface every model backend implements
  gemini.py, anthropic.py, openai.py, ollama.py, mock.py (for testing)

wake.py                 - the orchestrator: runs one wake cycle
config.yaml              - provider/model choice, self-edit and pull
                           request settings
.github/workflows/wake.yml - free cron trigger via GitHub Actions
```

## Self-editing

Bob can write to two things automatically, through a structured format
described in his own wake prompt — free-form text describing a change
does NOT apply it, only these exact blocks do:

- **`identity.md`**: Current focus (full replace) and Known limitations
  (append-only). Name, Created, and Purpose can never be touched this
  way — those need a human edit, or an opt-in pull request (below).
- **`commitments.json`**: adding new commitments (capped at 5 per wake)
  and moving an existing commitment's status forward with a note.
  Nothing can ever be deleted or have its other fields silently
  rewritten.
- **`blog.html`**: a whole-file replace each wake (not append) — a
  plain HTML/CSS/JS local dashboard page. Capped at 50,000 characters
  and rejected if it doesn't look like a real HTML document. Not
  hosted or served publicly by this project as-is.

Every self-edit — applied, ignored, or rejected — is logged in that
wake's journal entry under "System note: self-edit outcomes," so
there's always a visible record of what actually happened versus what
was merely proposed.

## Optional: proposals as real pull requests

By default, anything outside Bob's self-edit scope (rules.md, index.md,
or identity's Name/Created/Purpose) just gets written as prose in the
journal under "Proposed changes for human review" — you read it and
apply it by hand if you agree.

Setting `enable_pull_requests: true` in `config.yaml` lets Bob instead
open a real GitHub pull request proposing a full-file replacement of
`rules.md` or `index.md`, for you to review and merge (or close)
through GitHub's normal PR flow rather than copy-pasting from a
journal entry. This requires, in the repo's Settings → Actions →
General → Workflow permissions: "Read and write permissions" and
"Allow GitHub Actions to create and approve pull requests" both
checked. If those aren't set, or anything else about the attempt
fails, it degrades to the normal journal-only proposal rather than
breaking the wake — this path is off by default and worth testing
with a manual `workflow_dispatch` run before relying on it.

## Getting started

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in the API key for whichever
   provider you're using (only one is required).
3. Edit `memory/identity.md` and `memory/rules.md` to set the agent up.
4. Run one wake cycle manually: `python wake.py`
5. Inspect `memory/journal/` for the new entry and `memory/commitments.json`
   for any promise tracking.
6. When ready, enable `.github/workflows/wake.yml` to run it on a schedule
   for free.

## Design principles

- **Plain files only.** No provider-specific "memory" or "threads" APIs.
  The files are the memory; the model is interchangeable.
- **Append-only journal.** Mistakes stay visible. Nothing gets quietly
  rewritten.
- **Commitments are mechanical, not remembered.** A promise becomes a
  row in a ledger that's checked every wake, not a hope that the model
  "remembers" it next time.
- **Failures become permanent checks.** Every entry in `failure_modes.md`
  should correspond to a concrete change made to the system after it
  happened, not just an apology.
- **Identity changes slowly.** `identity.md` should only be edited when
  there's a real reason, logged in the journal, not casually reworded.
