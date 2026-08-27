# Wake Scaffold

A vendor-agnostic memory system for a stateless AI agent that "wakes up"
on a schedule with no memory of previous sessions except what it wrote
to disk.

This project is not about which LLM is used. It's about the memory
architecture: how a model with zero built-in continuity can behave like
something with a persistent identity, using nothing but files, discipline,
and mechanical checks.

## Core idea

Every wake, the agent:
1. Reads a small, curated set of files (not its entire history)
2. Does its work
3. Writes exactly one immutable journal entry
4. Updates its commitments ledger
5. Occasionally consolidates the journal into a smaller summary

The model backend is swappable. See `providers/`.

## Structure

```
memory/
  identity.md          - who the agent is, updated only on real evidence
  rules.md             - hard constraints, read every wake
  commitments.json      - promises made, tracked to completion
  failure_modes.md      - named, dated log of memory failures and fixes
  index.md               - periodically-refreshed summary of everything known
  journal/
    2026-08-26-0001.md   - one append-only file per wake, never edited after

providers/
  base.py               - the interface every model backend implements
  gemini.py, anthropic.py, openai.py, ollama.py

wake.py                 - the orchestrator: runs one wake cycle
config.yaml              - model choice, schedule metadata, price ceilings etc
.github/workflows/wake.yml - free cron trigger via GitHub Actions
```

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
