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
  blog.html                - a plain HTML/CSS/JS page, mechanically
                           rendered from blog_posts.json every time a
                           post is added — never written directly by
                           Bob, so a post can't be lost by a bad
                           generation. Local file only, not hosted.
  blog_posts.json           - the actual append-only source of truth
                           for the blog. Each post is added once and
                           never rewritten or removed.
  core_memories.json        - a small, capped (see MAX_CORE_MEMORIES
                           in wake.py), append-only list of
                           self-nominated formative lessons, read into
                           every wake's reflection.
  journal/
    2026-08-29-040827.md          - one append-only file per wake, never
                                  edited after. Filename is the exact
                                  local time the wake happened (see
                                  "timezone" in config.yaml), so files
                                  sort chronologically by name.
    2026-08-29-040827-FAILED.md   - written instead of a normal entry
                                  when a wake's API call fails, so a
                                  failure never just vanishes silently.
                                  Same naming scheme, "-FAILED" at the
                                  end so it still sorts in time order.

base_memory/
  Complete seed template for a new identity. It includes the empty
  blog_posts.json, core_memories.json, growth_plan.json, and journal/
  directory as well as the Markdown and commitment files. The lifecycle
  commands copy it; normal wakes never read or alter it.

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
- **`blog.html` / `blog_posts.json`**: adding one new post per wake
  (title + body content only — the page shell and styling are fixed
  Python code, not model-generated). Posts are never replaced or
  removed; blog.html is re-rendered from the full accumulated list
  every time, most recent post first, each one linked to the journal
  entry that created it. This is deliberately different from the
  identity/commitments pattern — there's no "sacred" section to
  protect, but there IS a structural guarantee (append-only storage +
  code-driven rendering) that replaces trusting the model to remember
  and re-include every past post correctly, which turned out to be
  fragile in practice.
- **`core_memories.json`**: adding one rare, formative lesson, capped
  at `MAX_CORE_MEMORIES` total (20 by default) — not a growing log,
  a small curated set read into every wake's reflection so it can
  actually shape decisions. Once full, adding more requires a human
  decision about what to retire; nothing self-edits past the cap.
  This is a modest, honest first step toward "memories that shape
  behavior the way personality traits do" — not a true
  relevance-triggered associative recall system (that would need
  embeddings and similarity search, a materially bigger project).

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
journal entry. GitHub supplies a short-lived `GITHUB_TOKEN` automatically
for each workflow run; the included workflow passes it to the wake process.
In the repo's Settings → Actions → General → Workflow permissions, choose
"Read and write permissions" and enable "Allow GitHub Actions to create and
approve pull requests." If those aren't set, or anything else about the attempt
fails, it degrades to the normal journal-only proposal rather than
breaking the wake — this path is off by default and worth testing
with a manual `workflow_dispatch` run before relying on it.

## Timezone

Every timestamp this project writes — journal filenames, the "Woke:"
line inside each entry, `identity.md`'s "Last updated", and the
`made_on`/status dates in `commitments.json` — uses the timezone set
in `config.yaml` (`timezone: America/Los_Angeles` by default). Bob is
also explicitly told the current local time at the start of each wake,
so anything he writes into `blog.html` or elsewhere should reflect it
too, rather than guessing from file contents.

This uses Python's `zoneinfo`, so daylight saving (PDT ↔ PST) is
handled automatically — nothing to adjust by hand twice a year. The
one exception is the *cron schedule itself* in
`.github/workflows/wake.yml`: GitHub Actions cron is always UTC, so
that still needs a manual one-hour shift when DST changes if you want
the scheduled run time to stay pinned to a specific local time.

`memory/journal/`'s naming scheme was old-UTC-based before
(`2026-08-28-0001.md`, `FAILED-2026-08-28T161327.md`) and is now
local-time-based (`2026-08-28-025254.md`,
`2026-08-28-091327-FAILED.md`). `scripts/migrate_journal_filenames.py`
renames existing old-scheme files to match — it only renames, never
edits file contents, so it doesn't violate the append-only rule these
files are supposed to follow. Run `python scripts/migrate_journal_filenames.py --dry-run`
first to preview, then without `--dry-run` to actually rename.

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

## Identity lifecycle

Each active identity lives in `memory/`. To preserve its full history and
start clean, use the lifecycle commands instead of manually renaming or
copying directories:

```bash
# Archive the active identity unchanged as memory_bob/
python wake.py archive --as bob

# Create a complete new active identity from base_memory/
python wake.py new --name "Ada" --purpose "Build and test small, repeatable research tools."

# Or do both in one operation after choosing the new identity's name and purpose
python wake.py reset --archive-as bob --name "Ada" --purpose "Build and test small, repeatable research tools."
```

The reset command checks the template and the new identity details before it
moves the active directory. Archives are never edited by the wake loop. A new
identity begins with empty journals, commitments, blog posts, core memories,
and a capability-growth plan; it does not inherit the prior identity's
persona or unfinished tasks.

## Growth through work

The wake loop now limits reflection to selecting work and asks the identity to
leave evidence behind: a durable artifact, evaluated experiment, tested repair,
or reviewable proposal. `growth_plan.json` is a small project backlog with
evidence-based status history. A blog post is optional and should describe a
completed result—not serve as a diary entry or a substitute for the work.

This remains a deliberately bounded system. The model can update its approved
memory records and propose changes for human review; it cannot silently modify
its own source code or grant itself new permissions. That boundary makes each
new capability reviewable rather than merely claimed.

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
