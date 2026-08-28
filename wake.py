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
import re
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
        "You do NOT have the ability to directly edit rules.md, index.md, "
        "or the Name/Created/Purpose fields of identity.md — propose "
        "changes to those inside your journal text under a heading like "
        "'Proposed changes for human review' instead. Those fields define "
        "who you are at a level stable enough that only a human should "
        "change them.\n\n"
        "You DO have narrow, automatic write access to two things, and "
        "only through the exact structured mechanism below — free text "
        "describing a change does NOT apply it, only these blocks do:\n\n"
        "**To update your Current focus or add a Known limitation**, "
        "include a fenced block:\n"
        "```identity-update\n"
        '{"current_focus": "new focus text, optional",\n'
        ' "known_limitations_add": ["a new limitation you genuinely '
        'observed this wake, optional"]}\n'
        "```\n"
        "Only include a key if you're actually changing it. Any other key "
        "(name, purpose, created, etc.) will be ignored, not applied. "
        "known_limitations_add only ever appends — it can't remove or "
        "rewrite past limitations, since those are honest historical "
        "observations even if later superseded.\n\n"
        "**To add a new commitment or change an existing one's status**, "
        "include a fenced block:\n"
        "```commitments-update\n"
        '{"add": [{"to": "...", "what": "...", "due": "YYYY-MM-DD"}],\n'
        ' "status_change": [{"id": "...", "new_status": "open|in_progress|'
        'blocked|closed", "note": "..."}]}\n'
        "```\n"
        "You can never delete a commitment or rewrite an existing one's "
        "fields outright — only add new ones or move an existing one's "
        "status forward with a note explaining why. Up to 5 adds per "
        "wake; anything beyond that is ignored.\n\n"
        "Both blocks are optional. Explain your reasoning in prose before "
        "any block you include — the reasoning is saved in the journal "
        "even though it isn't itself machine-applied.",
    ])


def extract_block(text: str, tag: str) -> str | None:
    """Pull the content of a ```tag ... ``` fenced block out of model
    output. Returns None if the block isn't present."""
    pattern = rf"```{tag}\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


MAX_FIELD_LEN = 2000
MAX_ADDS_PER_WAKE = 5
ALLOWED_STATUSES = {"open", "in_progress", "blocked", "closed"}


def apply_identity_update(raw_json: str) -> list[str]:
    """
    Apply ONLY current_focus (replace) and known_limitations_add (append)
    to identity.md, via precise field-level regex substitution. Name,
    Created, and Purpose are never touched by this path no matter what
    the model includes — those require a human edit. Any other key in
    the JSON is silently ignored (not applied), and that's logged.
    """
    notes = []
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED identity-update: not valid JSON ({e}). No changes applied."]
    if not isinstance(data, dict):
        return ["REJECTED identity-update: must be a JSON object. No changes applied."]

    allowed_keys = {"current_focus", "known_limitations_add"}
    ignored_keys = set(data.keys()) - allowed_keys
    if ignored_keys:
        notes.append(
            f"IGNORED unauthorized identity fields (not applied): {sorted(ignored_keys)}"
        )

    path = MEMORY / "identity.md"
    if not path.exists():
        return notes + ["REJECTED identity-update: identity.md not found."]
    text = path.read_text()
    changed = False

    if "current_focus" in data:
        new_value = str(data["current_focus"]).strip()[:MAX_FIELD_LEN]
        if new_value:
            pattern = re.compile(r"(\*\*Current focus:\*\*)(.*?)(?=\n\n\*\*|\Z)", re.DOTALL)
            if pattern.search(text):
                text = pattern.sub(lambda m: m.group(1) + " " + new_value + "\n\n", text, count=1)
                notes.append(f"APPLIED current_focus update: {new_value[:100]}"
                             + ("..." if len(new_value) > 100 else ""))
                changed = True
            else:
                notes.append("REJECTED current_focus update: field not found in identity.md.")

    if "known_limitations_add" in data:
        items = data["known_limitations_add"]
        if isinstance(items, str):
            items = [items]
        if isinstance(items, list) and items:
            bullets = "\n".join(
                f"- {str(i).strip()[:MAX_FIELD_LEN]}" for i in items if str(i).strip()
            )
            if bullets:
                pattern = re.compile(r"(\*\*Known limitations:\*\*)(.*?)(?=\n\n\*\*|\Z)", re.DOTALL)
                m = pattern.search(text)
                if m:
                    existing = m.group(2).strip()
                    # Template placeholder text is always parenthetical
                    # instructions, not a real observation — clear it
                    # instead of appending a real bullet after it.
                    is_placeholder = existing.startswith("(") or not existing
                    prior = "" if is_placeholder else existing + "\n"
                    new_block = m.group(1) + "\n" + prior + bullets + "\n\n"
                    text = text[:m.start()] + new_block + text[m.end():]
                    notes.append(f"APPLIED {len(items)} new known limitation(s).")
                    changed = True
                else:
                    notes.append("REJECTED known_limitations_add: field not found in identity.md.")

    if changed:
        text = re.sub(r"\n{3,}", "\n\n", text)  # collapse accumulated blank lines

    if changed:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
        last_updated = re.compile(r"\*\*Last updated:\*\*.*")
        replacement = f"**Last updated:** {date} — reason: self-edit via wake cycle"
        text = last_updated.sub(replacement, text, count=1) if last_updated.search(text) \
            else text + f"\n\n{replacement}\n"
        path.write_text(text)

    if not notes:
        notes.append("No recognized identity fields present in identity-update block.")
    return notes


def apply_commitments_update(raw_json: str) -> list[str]:
    """
    Apply ONLY additive/status-forward operations to commitments.json:
    add new commitments (validated) or move an existing commitment's
    status forward with a note. Never accepts a full-list replacement,
    so an existing commitment can never be silently deleted or have its
    other fields rewritten by a self-edit.
    """
    notes = []
    try:
        ops = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED commitments-update: not valid JSON ({e}). No changes applied."]
    if not isinstance(ops, dict):
        return ["REJECTED commitments-update: must be a JSON object. No changes applied."]

    path = MEMORY / "commitments.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {"commitments": []}
    except json.JSONDecodeError:
        return ["REJECTED commitments-update: existing commitments.json is corrupted; "
                "fix it manually before self-edits can be applied."]
    commitments = data.setdefault("commitments", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    changed = False

    adds = ops.get("add", [])
    if isinstance(adds, list):
        for i, new_c in enumerate(adds[:MAX_ADDS_PER_WAKE]):
            if not isinstance(new_c, dict) or not {"to", "what", "due"}.issubset(new_c):
                notes.append(f"SKIPPED add #{i+1}: missing required field(s) (to/what/due).")
                continue
            new_id = f"c-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{i}"
            entry = {
                "id": new_id,
                "made_on": today,
                "to": str(new_c["to"]).strip()[:200],
                "what": str(new_c["what"]).strip()[:500],
                "due": str(new_c["due"]).strip()[:50],
                "status": "open",
                "status_history": [{"date": today, "status": "open",
                                     "note": "created via self-edit"}],
            }
            commitments.append(entry)
            notes.append(f"ADDED commitment {new_id}: {entry['what'][:80]}")
            changed = True
        if len(adds) > MAX_ADDS_PER_WAKE:
            notes.append(f"IGNORED {len(adds) - MAX_ADDS_PER_WAKE} additional add(s) "
                         f"past the {MAX_ADDS_PER_WAKE}-per-wake cap.")

    for change in ops.get("status_change", []):
        if not isinstance(change, dict):
            continue
        cid = change.get("id")
        new_status = change.get("new_status")
        note = str(change.get("note", "")).strip()[:500]
        if new_status not in ALLOWED_STATUSES:
            notes.append(f"SKIPPED status_change for {cid!r}: invalid status {new_status!r}.")
            continue
        match = next((c for c in commitments if c.get("id") == cid), None)
        if not match:
            notes.append(f"SKIPPED status_change: id {cid!r} not found.")
            continue
        match["status"] = new_status
        match.setdefault("status_history", []).append(
            {"date": today, "status": new_status, "note": note}
        )
        notes.append(f"UPDATED commitment {cid} -> {new_status}")
        changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n")
    if not notes:
        notes.append("No valid operations present in commitments-update block.")
    return notes


def apply_self_edits(model_output: str) -> str:
    """
    Look for identity-update / commitments-update blocks in the journal
    output and apply them if valid, via the narrow structured functions
    above. Returns a short system note summarizing what was applied,
    ignored, or rejected — appended visibly to the journal, never hidden.
    """
    all_notes = []

    identity_block = extract_block(model_output, "identity-update")
    if identity_block is not None:
        all_notes.extend(apply_identity_update(identity_block))

    commitments_block = extract_block(model_output, "commitments-update")
    if commitments_block is not None:
        all_notes.extend(apply_commitments_update(commitments_block))

    if not all_notes:
        return ""
    return "\n\n---\n\n## System note: self-edit outcomes\n\n" + "\n".join(
        f"- {n}" for n in all_notes
    )


def next_journal_filename() -> str:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
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

    # Apply any identity.md / commitments.json self-edits the model
    # included in its output, then append the outcome (applied/rejected)
    # to the journal text so it's part of the permanent record.
    self_edit_notes = apply_self_edits(output)
    output_with_notes = output + self_edit_notes

    path = write_journal_entry(reflection, output_with_notes, provider_name)

    print(f"Wake complete. Journal entry written: {path}")
    if self_edit_notes:
        print("Self-edit outcomes:" + self_edit_notes.replace("\n\n---\n\n## System note: self-edit outcomes\n\n", "\n"))
    print(
        "\nNote: rules.md and index.md changes are still proposal-only — "
        "review the journal for any 'Proposed changes for human review' "
        "section before applying those by hand."
    )


if __name__ == "__main__":
    sys.exit(main())