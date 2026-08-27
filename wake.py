"""
Runs one wake cycle:
  1. Read identity, rules, index, and open commitments (NOT the full journal)
  2. Call the model
  3. Write one new, immutable journal entry
  4. Remind the operator that commitments.json and index.md need review

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


def build_system_prompt() -> str:
    return "\n\n---\n\n".join([
        "You are waking up with no memory of any previous session except "
        "what is written below. Everything you know about your own past "
        "comes from these files. Do not invent history that isn't here.",
        "## IDENTITY\n" + read(MEMORY / "identity.md"),
        "## RULES (hard constraints, follow exactly)\n" + read(MEMORY / "rules.md"),
        "## CURRENT KNOWLEDGE (summary)\n" + read(MEMORY / "index.md"),
        "## OPEN COMMITMENTS (check these before claiming anything is done)\n"
        + load_open_commitments(),
    ])


def next_journal_filename() -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = sorted(JOURNAL.glob(f"{date}-*.md"))
    n = len(existing) + 1
    return f"{date}-{n:04d}.md"


def write_journal_entry(model_output: str, backend_name: str):
    JOURNAL.mkdir(parents=True, exist_ok=True)
    filename = next_journal_filename()
    path = JOURNAL / filename
    header = (
        f"# Session {filename[:-3]}\n\n"
        f"**Woke:** {datetime.now(timezone.utc).isoformat()}\n"
        f"**Model backend:** {backend_name}\n\n"
    )
    footer = (
        "\n\n---\n*This entry is append-only. If something here turns out "
        "to be wrong, say so in a future entry — do not edit this one.*\n"
    )
    path.write_text(header + model_output + footer)
    return path


def main():
    config = load_config()
    provider_name = config.get("provider", "gemini")
    model = config.get("model")

    provider = get_provider(provider_name, model)

    system_prompt = build_system_prompt()
    user_prompt = (
        "This is a new wake cycle. Based on your identity, rules, current "
        "knowledge, and open commitments above, decide what to work on and "
        "do it. Then write your journal entry for this session covering: "
        "what you read, what you did, what you decided and why, which "
        "commitment IDs (if any) you touched and their new status, and any "
        "uncertainties or flags for next time. Be concrete and specific — "
        "avoid vague or inflated language about your own progress."
    )

    try:
        output = provider.generate(system_prompt, user_prompt)
    except Exception as e:
        # A failed wake should leave a record, not just vanish into a CI
        # log nobody's watching. This does NOT count as a journal entry
        # about the agent's work — it's an operational failure log.
        JOURNAL.mkdir(parents=True, exist_ok=True)
        fail_path = JOURNAL / f"FAILED-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%S')}.md"
        fail_path.write_text(
            f"# Wake FAILED\n\n"
            f"**Attempted:** {datetime.now(timezone.utc).isoformat()}\n"
            f"**Provider:** {provider_name}\n"
            f"**Error:** {type(e).__name__}: {e}\n\n"
            f"No journal entry was produced this wake. Check credentials, "
            f"rate limits, and provider status before the next scheduled run.\n"
        )
        print(f"Wake FAILED — see {fail_path}", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1

    path = write_journal_entry(output, provider_name)

    print(f"Wake complete. Journal entry written: {path}")
    print(
        "\nReminder: review this entry for any commitments or identity "
        "changes that should be applied to memory/commitments.json or "
        "memory/identity.md before the next wake."
    )


if __name__ == "__main__":
    sys.exit(main())
