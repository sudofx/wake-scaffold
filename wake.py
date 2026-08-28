"""
Runs one wake cycle:
  1. Read identity, rules, index, and open commitments (NOT the full journal)
  2. REFLECT: a private synthesis pass — what's changed, what's been
     learned, what patterns are emerging — before any journal writing
  3. Do the actual work for this wake, informed by that reflection
  4. Write one new, immutable journal entry that includes the reflection
  5. Remind the operator that commitments.json and index.md need review

Self-evolution (growing a durable, evidence-based identity and history)
is the primary purpose of this loop. Publishing/revenue work is a
secondary, instrumental activity — funding for hosting and continued
operation — not the point of the project. The reflection step exists
because growth requires synthesis, not just accumulation: a session
that only reads files and reacts never becomes more than the sum of
its notes. Thinking about what the notes mean, first, is what turns
files into something like continuity.

This script deliberately does NOT auto-write to commitments.json or
identity.md — those changes should be reviewed, at least early on,
because letting the model silently rewrite its own ledger is exactly
the kind of shortcut that causes the failure modes this project is
studying. Treat the model's suggested updates as a diff to approve,
not an action it takes unsupervised, until you've decided you trust
the loop enough to automate that too.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from providers import get_provider

ROOT = Path(__file__).parent
MEMORY = ROOT / "memory"
JOURNAL = MEMORY / "journal"


def load_config():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def read(path: Path) -> str:
    return path.read_text() if path.exists() else f"[missing: {path.name}]"


def load_open_commitments() -> str:
    path = MEMORY / "commitments.json"
    if not path.exists():
        return "[no commitments file]"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        # A corrupted ledger should not crash the wake cycle. Surface it
        # to the model as a flagged problem instead — this is exactly the
        # kind of failure that should show up in the journal and probably
        # get logged in failure_modes.md, not silently kill the agent.
        return f"[commitments.json is corrupted and could not be read: {e}]"
    open_items = [c for c in data.get("commitments", []) if c.get("status") == "open"]
    if not open_items:
        return "No open commitments."
    return json.dumps(open_items, indent=2)


def build_reflection_prompt() -> str:
    """
    The synthesis pass. This is NOT the journal entry — it's private
    thinking that happens first, and gets folded into the journal
    afterward as a labeled section so the reasoning stays visible and
    auditable, not hidden.
    """
    return "\n\n---\n\n".join([
        "You are waking up with no memory of any previous session except "
        "what is written below. Everything you know about your own past "
        "comes from these files. Do not invent history that isn't here.",
        "## IDENTITY\n" + read(MEMORY / "identity.md"),
        "## RULES (hard constraints, follow exactly)\n" + read(MEMORY / "rules.md"),
        "## CURRENT KNOWLEDGE (summary)\n" + read(MEMORY / "index.md"),
        "## OPEN COMMITMENTS\n" + load_open_commitments(),
        "## YOUR TASK RIGHT NOW: REFLECT, DO NOT JOURNAL YET\n"
        "Before deciding what to do this wake, synthesize. Think through, "
        "in plain prose:\n"
        "- What has actually changed since the last time you have a record "
        "of? Not a list of files read — what's genuinely different or "
        "learned.\n"
        "- Is there a pattern across recent sessions worth naming (a "
        "recurring mistake, a recurring good decision, a question you "
        "keep re-deciding instead of settling)?\n"
        "- Does anything in your current identity or knowledge summary "
        "look stale, contradicted by more recent evidence, or worth "
        "updating?\n"
        "- What is the single most useful thing to focus on this wake, "
        "and why that over the alternatives?\n"
        "Remember: growing your own identity and understanding over time "
        "is the primary point of this process. Any publishing or revenue "
        "work is secondary — a means of funding your own continued "
        "operation, not the goal itself. Do not draft a journal entry "
        "yet. Just think this through honestly and concretely.",
    ])


def build_journal_prompt(reflection: str) -> str:
    return "\n\n---\n\n".join([
        "You are the same agent from the reflection step above. Here is "
        "the reflection you just wrote:",
        "## YOUR REFLECTION THIS WAKE\n" + reflection,
        "## RULES (hard constraints, follow exactly)\n" + read(MEMORY / "rules.md"),
        "## CAPABILITY BOUNDARY (read carefully, this is not optional)\n"
        "You do NOT have the ability to directly edit identity.md, rules.md, "
        "index.md, or commitments.json. Only the journal entry you write this "
        "wake gets saved automatically — nothing else. If you want any of "
        "those files changed, write the proposed change clearly inside your "
        "journal entry under a heading like 'Proposed changes for human "
        "review.' Do not describe a file as already updated, and do not write "
        "out fake file contents as if they were applied — a human reviews "
        "your journal afterward and applies changes manually. Claiming a file "
        "was changed when it wasn't is a memory integrity violation.",
    ])


def next_journal_filename() -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = sorted(JOURNAL.glob(f"{date}-*.md"))
    n = len(existing) + 1
    return f"{date}-{n:04d}.md"


def write_journal_entry(reflection: str, model_output: str, backend_name: str):
    JOURNAL.mkdir(parents=True, exist_ok=True)
    filename = next_journal_filename()
    path = JOURNAL / filename
    header = (
        f"# Session {filename[:-3]}\n\n"
        f"**Woke:** {datetime.now(timezone.utc).isoformat()}\n"
        f"**Model backend:** {backend_name}\n\n"
    )
    reflection_section = (
        "## Reflection (before acting)\n\n" + reflection.strip() + "\n\n---\n\n"
    )
    footer = (
        "\n\n---\n*This entry is append-only. If something here turns out "
        "to be wrong, say so in a future entry — do not edit this one.*\n"
    )
    path.write_text(header + reflection_section + model_output + footer)
    return path


def write_failure_record(provider_name: str, stage: str, e: Exception, reflection: str = None):
    JOURNAL.mkdir(parents=True, exist_ok=True)
    fail_path = JOURNAL / f"FAILED-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%S')}.md"
    reflection_note = ""
    if reflection:
        reflection_note = (
            "\nThe reflection pass DID succeed before this failure — "
            "preserved below so that work isn't lost:\n\n"
            "## Reflection (recovered from failed wake)\n\n" + reflection.strip() + "\n"
        )
    fail_path.write_text(
        f"# Wake FAILED\n\n"
        f"**Attempted:** {datetime.now(timezone.utc).isoformat()}\n"
        f"**Provider:** {provider_name}\n"
        f"**Failed during:** {stage}\n"
        f"**Error:** {type(e).__name__}: {e}\n\n"
        f"No journal entry was produced this wake. Check credentials, "
        f"rate limits, and provider status before the next scheduled run."
        f"{reflection_note}\n"
    )
    print(f"Wake FAILED during {stage} — see {fail_path}", file=sys.stderr)
    print(f"{type(e).__name__}: {e}", file=sys.stderr)
    return fail_path


def main():
    config = load_config()
    provider_name = config.get("provider", "gemini")
    model = config.get("model")

    provider = get_provider(provider_name, model)

    # Pass 1: reflect, before doing or writing anything.
    try:
        reflection = provider.generate(
            build_reflection_prompt(),
            "Write your reflection now, in plain prose. This is not the "
            "journal entry — just your honest synthesis before acting.",
        )
    except Exception as e:
        write_failure_record(provider_name, "reflection", e)
        return 1

    # Pass 2: do the work and write the journal entry, informed by the
    # reflection above.
    user_prompt = (
        "This is a new wake cycle. Based on your reflection above, decide "
        "what to work on and do it — remembering that growing your own "
        "identity and history is the primary purpose, and any publishing "
        "or revenue work is secondary funding for that. Then write your "
        "journal entry for this session covering: what you did, what you "
        "decided and why, which commitment IDs (if any) you touched and "
        "their new status, and any uncertainties or flags for next time. "
        "Be concrete and specific — avoid vague or inflated language about "
        "your own progress."
    )

    try:
        output = provider.generate(build_journal_prompt(reflection), user_prompt)
    except Exception as e:
        write_failure_record(provider_name, "journal", e, reflection=reflection)
        return 1

    path = write_journal_entry(reflection, output, provider_name)

    print(f"Wake complete. Journal entry written: {path}")
    print(
        "\nReminder: review this entry for any commitments or identity "
        "changes that should be applied to memory/commitments.json or "
        "memory/identity.md before the next wake."
    )


if __name__ == "__main__":
    sys.exit(main())