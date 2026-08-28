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

    system_prompt = build_system_promp
