# Wake Scaffold

See [`IDENTITIES.md`](IDENTITIES.md) for the current identity's blog and
every archived identity's — it's the authoritative, self-updating list,
so a link here would go stale the moment an identity is archived.


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
  growth_plan.json          - a small backlog of capability projects
                           ("can I build this?"), each with a status
                           history and evidence field.
  hypotheses.json           - a self-experiment tracker ("is this
                           true?"): prediction, test method, real
                           evidence, conclusion. See "Self-editing"
                           below.
  tool_runs.json            - the last MAX_TOOL_RUN_HISTORY tool-run
                           results (stdout/stderr/exit code), written
                           by tool-run and read back as evidence in
                           the next wake's TOOL RUN HISTORY section.
  tools/
    validate_memory.py            - a tool file written via tool-write,
                                  executed via tool-run. Anything the
                                  agent has built and can now run lives
                                  here, plain Python files only.
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

## Keeping the template in sync

`memory/rules.md` (the active identity's copy) and `base_memory/rules.md`
(the seed template every new identity is bootstrapped from) will drift
over time, and that's expected — but not every drift should be resolved
the same way. Before editing either file, diff them and ask which kind
of change this is:

- **Structural/mechanical** (a mechanism the wake loop itself enforces —
  a block format, a cap, a required section, a hard constraint like
  "never fabricate a human experience") must be applied to **both**
  files, identically. If it's true of how the loop works, it should be
  true for every identity that's ever bootstrapped from the template,
  not just the current one.
- **Voice/tone/persona** (how Bob's own Publishing section describes his
  particular writing style — e.g. a specific voice a given identity has
  developed) stays **only** in the active identity's `memory/rules.md`
  and must **not** be pushed to `base_memory/rules.md`. A future
  identity should start from a neutral template, not inherit a prior
  identity's personality.

When in doubt, ask: would this line make sense for an identity that
hasn't been created yet? If yes, it's structural — sync it. If it only
makes sense because of who Bob specifically has become, it's persona —
leave it where it is.

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
- **`growth_plan.json`**: adding a capability project (title,
  capability, next_step) or moving an existing one's status forward
  (`proposed -> active -> complete`, or `blocked`) with evidence. A
  project about a tool can only be marked `complete` once a `tool-run`
  has actually produced a result in `tool_runs.json` — writing or
  editing the tool's code is never itself evidence that it works.
  Recording a new known limitation via `identity-update` automatically
  spawns one of these projects, exploring whether an honest workaround
  exists — see "Known limitations" below.
- **`hypotheses.json`**: recording a self-experiment — a specific,
  falsifiable prediction plus how it will actually be tested — or
  resolving one with real evidence and a conclusion. This is separate
  from `growth_plan.json`: a growth project asks "can I build this?",
  a hypothesis asks "is this true?" (about the agent itself, its
  environment, or an assumption it's relying on). Moving a hypothesis
  to any status besides `testing` is rejected outright unless real
  evidence is supplied — evidence has to describe something that
  actually happened, not restate the prediction.
- **`tools/` via `tool-write` and `tool-run`**: two separate
  mechanisms, because writing code and running it are different
  claims:
  - `tool-write` saves 1–3 plain files (`.py`/`.md`/`.txt`/`.json`,
    no subfolders, 20,000-byte cap each) into `memory/tools/`. This
    only writes bytes to disk — it never executes anything.
  - `tool-run` executes one already-written `.py` file from
    `memory/tools/` with Python, capped at 2 runs per wake, a
    15-second timeout, and 4,000-character-truncated stdout/stderr.
    The result (exit code, stdout, stderr) is appended to
    `tool_runs.json`, which is what shows up as real evidence in the
    *next* wake's reflection prompt — a run started this wake isn't
    visible to the same wake that started it.

  **Sandboxing.** `tool-run`'s subprocess is deliberately restricted,
  though this is a best-effort measure built on plain `subprocess`,
  not a chroot or container — it will not stop a script that goes out
  of its way to open an arbitrary absolute path:
  - **Environment is rebuilt from an allowlist, never inherited.**
    `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
    `GITHUB_TOKEN`, and everything else in the real process
    environment are simply absent from the subprocess — see
    `SAFE_TOOL_ENV_ALLOWLIST` in `wake.py`. A tool file is text a
    model wrote; it has no legitimate reason to see credentials, and
    `subprocess.run()` inherits the *entire* parent environment by
    default unless `env=` is set explicitly, which is exactly the gap
    this closes.
  - **`cwd` is `memory/tools/`, not the repo root.** A script that
    opens a relative path by default lands inside its own tools
    directory, not next to `identity.md`, `rules.md`, `.env`, or the
    git history.
  - No network sandboxing is attempted — "no network access" is not
    guaranteed beyond whatever the host OS otherwise provides.

  A tool is "implemented" the wake it's written; it's only "verified
  working" once a `tool-run` result actually appears in
  `tool_runs.json`. The distinction matters for `growth_plan.json`
  evidence fields (see above) and for what the journal is allowed to
  claim under "Growth through work" in `rules.md`.

### Known limitations spawn a real question, not a static note

When a wake records a new known limitation via `identity-update`'s
`known_limitations_add`, the wake loop automatically adds a
`growth_plan.json` project asking whether there's an honest path
forward for it (`spawn_limitation_growth_projects` in `wake.py`).
That project follows the same evidence-based lifecycle as any other
capability project — it can conclude "yes, here's a legitimate
workaround," or it can conclude "no, disclosure is the only honest
option," and either is a complete, acceptable answer. What it can
never conclude, per `rules.md`'s "Limitations and workarounds"
section, is a workaround that crosses another rule's boundary or that
misrepresents to a reader, a reviewer, or the agent's own future self
what actually happened.

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

## Memory compression: a two-tier system

`core_memories.json` and `index.md` together are the compress/recall
system that keeps a normal wake's context small and cheap, even as the
journal grows indefinitely:

- **Read every wake (small, bounded, cheap):** `core_memories.json`
  (capped at `MAX_CORE_MEMORIES`, currently 20) and `index.md` (a
  hand/proposal-edited summary, not auto-generated). These are what
  `build_reflection_prompt` actually loads.
- **Detail layer (retrievable by reference, not re-read wholesale):**
  the full `journal/` history, `blog_posts.json`, and everything in
  `tool_runs.json` beyond the last 5 entries. Nothing in this layer is
  deleted or summarized away — it's just not reloaded into every
  prompt. Journal links already embedded in blog posts and core
  memories are how a reader (human or Bob) finds the detail when it's
  actually needed.

Because `index.md` is one of the few files Bob can only change via the
human-reviewed proposal mechanism (the same protection as `rules.md`),
nothing refreshes it automatically — it's easy for it to go stale
without anyone noticing. `build_reflection_prompt` includes a periodic
"MEMORY CONSOLIDATION CHECKPOINT" notice (see
`index_consolidation_interval_wakes` in `config.yaml`, every 15 wakes
by default) suggesting Bob check whether `index.md` still reflects
recent developments and propose a refresh if not — this is a nudge,
not a requirement, since consolidating a summary that's still accurate
would just waste a wake.

`format_hypotheses_for_prompt()` follows the same "read a bounded
summary, not the whole history" principle: every open (`testing`)
hypothesis is shown in full, but only the 3 most recently resolved
ones, with a count of how many earlier resolved hypotheses are omitted
— `hypotheses.json` itself keeps the full history, this only bounds
what's re-read into every prompt.

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

## Testing

`tests/test_wake.py` runs the self-edit mechanics directly, against a
throwaway `memory/`-shaped temp directory — never the real one, no API
key, no network, no waiting for a live scheduled wake:

```bash
python tests/test_wake.py
```

This includes an actual, run test — not just an inspection of the code
— confirming the mandatory blog-post fallback (`compose_fallback_blog_post`
+ `apply_blog_post`, wired through `apply_self_edits`) does its job:
when journal output has no `blog-post` block, a fallback post is added,
`blog.html` is re-rendered to include it, and a `WARNING: no blog-post
block this wake` note comes back; when the model *does* include a real
`blog-post` block (as `MockProvider`'s always does), the fallback path
is never exercised. It also runs `MockProvider`'s actual reflection and
journal prompts through the two-pass flow end to end, and separately
verifies the `tool-run` sandbox: a tool file that prints its own `cwd`
and dumps `os.environ` is written and executed for real, and the test
asserts the working directory is `memory/tools/` (not the repo root)
and that a secret only present in the *outer* test process's
environment never appears in the subprocess's output.

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
or reviewable proposal. `growth_plan.json` and `hypotheses.json` are small,
evidence-based backlogs — the former for capability projects, the latter for
self-experiments. A blog post is REQUIRED every wake per `rules.md`; if the
model skips it, the wake loop auto-composes a plain factual fallback post from
whatever else happened, and logs a warning — see "Actually test the blog
fallback" below.

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
