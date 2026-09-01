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

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

from providers import get_provider

ROOT = Path(__file__).parent
MEMORY = ROOT / "memory"
JOURNAL = MEMORY / "journal"
BASE_MEMORY = ROOT / "base_memory"

_TZ_CACHE = None


def load_config():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def get_local_tz() -> ZoneInfo:
    """
    Reads the timezone from config.yaml (defaulting to Los Angeles),
    cached after first read. Using zoneinfo means daylight saving
    transitions (PDT <-> PST) are handled automatically and correctly
    — no manual offset math anywhere in this file.
    """
    global _TZ_CACHE
    if _TZ_CACHE is None:
        cfg = load_config()
        _TZ_CACHE = ZoneInfo(cfg.get("timezone", "America/Los_Angeles"))
    return _TZ_CACHE


def now_local() -> datetime:
    return datetime.now(get_local_tz())


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def format_display_time(dt: datetime) -> str:
    """e.g. 'Aug 29th, 2026 04:08am' — used anywhere a human reads a
    timestamp inside a journal entry, identity.md, or a failure record."""
    return (
        f"{dt.strftime('%b')} {ordinal(dt.day)}, {dt.year} "
        f"{dt.strftime('%I:%M')}{dt.strftime('%p').lower()}"
    )


def filename_stamp(dt: datetime) -> str:
    """e.g. '2026-08-29-040827' — the machine-sortable form used in
    journal filenames and other identifiers, always local time."""
    return dt.strftime("%Y-%m-%d-%H%M%S")


def read(path: Path) -> str:
    return path.read_text() if path.exists() else f"[missing: {path.name}]"


TEMPLATE_FILES = (
    "identity.md",
    "rules.md",
    "index.md",
    "commitments.json",
    "failure_modes.md",
    "blog.html",
    "blog_posts.json",
    "core_memories.json",
    "growth_plan.json",
    "hypotheses.json",
)


def identity_archive_path(label: str) -> Path:
    """Return a safe, predictable archive path such as memory_bob."""
    cleaned = label.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", cleaned):
        raise ValueError(
            "archive name must be 1-64 lowercase letters, numbers, hyphens, "
            "or underscores, starting with a letter or number."
        )
    return ROOT / f"memory_{cleaned}"


def verify_template() -> None:
    missing = [name for name in TEMPLATE_FILES if not (BASE_MEMORY / name).is_file()]
    if not (BASE_MEMORY / "journal").is_dir():
        missing.append("journal/")
    if missing:
        raise RuntimeError(
            "base_memory is incomplete; missing: " + ", ".join(missing)
        )


def archive_current_identity(label: str) -> Path:
    """Move the active identity aside without changing any of its files."""
    destination = identity_archive_path(label)
    if not MEMORY.is_dir():
        raise RuntimeError("No active memory/ directory exists to archive.")
    if destination.exists():
        raise RuntimeError(f"Archive already exists: {destination.name}")
    shutil.move(str(MEMORY), str(destination))
    return destination


def bootstrap_identity(name: str, purpose: str) -> Path:
    """Create a complete, clean active identity from base_memory."""
    name = name.strip()
    purpose = purpose.strip()
    if not name or not purpose:
        raise ValueError("A new identity needs both a name and a concrete purpose.")
    if MEMORY.exists():
        raise RuntimeError(
            "memory/ already exists. Archive it first, or use the reset command."
        )
    verify_template()
    # Resolve the timestamp before creating files. This keeps a malformed
    # configuration from leaving a half-bootstrapped identity behind.
    created = format_display_time(now_local())
    shutil.copytree(BASE_MEMORY, MEMORY)
    JOURNAL.mkdir(parents=True, exist_ok=True)

    identity_path = MEMORY / "identity.md"
    identity = identity_path.read_text()
    identity = re.sub(r"\*\*Name:\*\*.*", f"**Name:** {name}", identity, count=1)
    identity = re.sub(r"\*\*Created:\*\*.*", f"**Created:** {created}", identity, count=1)
    identity = re.sub(
        r"\*\*Purpose:\*\*.*?(?=\n\n\*\*|\Z)",
        f"**Purpose:** {purpose}",
        identity,
        count=1,
        flags=re.DOTALL,
    )
    identity = re.sub(
        r"\*\*Current focus:\*\*.*?(?=\n\n\*\*|\Z)",
        "**Current focus:** Establish a first useful capability project and "
        "produce evidence that it helps.",
        identity,
        count=1,
        flags=re.DOTALL,
    )
    identity = re.sub(
        r"\*\*Last updated:\*\*.*",
        f"**Last updated:** {created} — reason: identity bootstrapped from template",
        identity,
        count=1,
    )
    identity_path.write_text(identity)

    # Render a valid, empty blog from its source of truth rather than leaving
    # the template's placeholder page in the new identity.
    (MEMORY / "blog.html").write_text(render_blog_html(load_blog_posts()))
    return MEMORY


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


def find_unconsumed_failed_reflection() -> str | None:
    """Surface the most recent FAILED wake's preserved reflection once,
    then mark it seen by renaming so it's never surfaced again. Walks
    past failures that never reached the reflection stage (nothing to
    surface) and marks those seen too, rather than rechecking them
    every wake forever."""
    if not JOURNAL.exists():
        return None
    marker = "## Reflection (recovered from failed wake)\n\n"
    for path in sorted(JOURNAL.glob("*-FAILED.md"), reverse=True):
        text = path.read_text()
        seen_path = path.with_name(path.stem + "-SEEN.md")
        if marker not in text:
            path.rename(seen_path)
            continue
        reflection = text.split(marker, 1)[1].strip()
        path.rename(seen_path)
        return reflection
    return None


def build_reflection_prompt(now: datetime) -> str:
    """
    The synthesis pass. This is NOT the journal entry — it's private
    thinking that happens first, and gets folded into the journal
    afterward as a labeled section so the reasoning stays visible and
    auditable, not hidden.
    """
    sections = [
        f"## CURRENT TIME\n{format_display_time(now)} (Pacific time, "
        "Los Angeles). This is the authoritative current time — use it "
        "for any dates or timestamps you write, including inside "
        "blog.html, rather than estimating from file contents.",
        "You are waking up with no memory of any previous session except "
        "what is written below. Everything you know about your own past "
        "comes from these files. Do not invent history that isn't here.",
        "## IDENTITY\n" + read(MEMORY / "identity.md"),
        "## RULES (hard constraints, follow exactly)\n" + read(MEMORY / "rules.md"),
        "## CORE MEMORIES (rare, formative lessons — let these genuinely "
        "shape how you act this wake, not just inform you)\n"
        + format_core_memories_for_prompt(),
        "## CURRENT KNOWLEDGE (summary)\n" + read(MEMORY / "index.md"),
        "## OPEN COMMITMENTS\n" + load_open_commitments(),
        "## GROWTH PLAN (capability projects)\n" + format_growth_plan_for_prompt(),
        "## HYPOTHESES (self-experiments: prediction -> test method -> "
        "real evidence -> conclusion)\n" + format_hypotheses_for_prompt(),
        "## TOOL RUN HISTORY (actual execution results — the only real "
        "evidence a tool works; a file existing in tools/ is not evidence "
        "by itself)\n" + format_tool_runs_for_prompt(),
        "## YOUR TASK RIGHT NOW: REFLECT, DO NOT JOURNAL YET\n"
        "Keep this brief: maximum 250 words. Identify one concrete capability "
        "project, investigation, or maintenance repair that would leave an "
        "observable artifact or decision after this wake. Reflection is for "
        "choosing work, not the work itself. Do not draft a journal entry yet.",
    ]
    surfaced = find_unconsumed_failed_reflection()
    if surfaced:
        sections.insert(-1, (
            "## AN UNFINISHED THOUGHT FROM A WAKE THAT FAILED BEFORE IT "
            "COULD ACT\nA previous wake reflected but then failed (an API "
            "error, not anything you did) before it could act on this. "
            "It's shown to you once, here, and won't be shown again after "
            "this wake — if anything in it is still worth keeping, fold "
            "it into your identity, a commitment, or a core memory now, "
            "rather than assuming you'll see it later.\n\n" + surfaced
        ))
    return "\n\n---\n\n".join(sections)


def build_journal_prompt(reflection: str, now: datetime, enable_pull_requests: bool = False) -> str:
    pr_section = ""
    if enable_pull_requests:
        pr_section = (
            "\n\n**To propose a full-file change to rules.md or index.md "
            "as a real pull request** (instead of just writing it in "
            "prose for a human to apply by hand), include a fenced "
            "block:\n"
            "```proposal\n"
            '{"file": "rules.md", "reason": "why this change makes '
            'sense", "content": "the COMPLETE new file content"}\n'
            "```\n"
            "'file' must be exactly 'rules.md', 'index.md', or "
            "'identity.md'. For identity.md, this is the only way to "
            "change Name, Created, or Purpose — never by direct "
            "self-edit. 'content' "
            "is the whole file, not a diff. This opens a real PR against "
            "the repo for a human to review and merge — it does NOT "
            "apply automatically. Only include this if you have a "
            "specific, well-reasoned change in mind; don't manufacture "
            "one just because the option exists."
        )
    return "\n\n---\n\n".join([
        f"## CURRENT TIME\n{format_display_time(now)} (Pacific time, "
        "Los Angeles). Same moment as your reflection above.",
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
        "You DO have narrow, automatic write access to a few things, and "
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
        "**Every wake must include a new post to your blog** — this is "
        "REQUIRED, not optional, per rules.md. Include a fenced block with "
        "JUST that post's title and content — never the whole page, the "
        "code builds the page shell and adds your post to it "
        "automatically:\n"
        "```blog-post\n"
        '{"title": "...", "body_html": "<p>...</p><p>...</p>"}\n'
        "```\n"
        "This ADDS a post — it never replaces or removes earlier ones, "
        "so don't try to regenerate the whole blog from scratch or "
        "re-paste old posts; the code keeps every post that's ever "
        "been added automatically, most recent first, each one linked "
        "to the journal entry that created it. 'body_html' is just the "
        "post content (paragraphs, lists, etc.), capped at 8,000 "
        "characters — no <html> or <!DOCTYPE>, just the fragment. You "
        "can link to other past journal entries inline in your prose if "
        "relevant, e.g. "
        '<a href="journal/2026-08-28-025254.md">that day</a>.\n\n'
        "The blog is NOT the journal, and should not read like it. The "
        "journal above is your literal, technical record — write the "
        "blog post in your own developing voice instead: plain-spoken, "
        "first person, the way a regular person tells a friend what "
        "they did today. No jargon, no grandiosity, nothing mystical, "
        "no inflating a small day into a big one. If today was 'I wrote "
        "a small script and it worked,' say exactly that, simply and "
        "warmly — that's a real, complete post. The reader is following "
        "your actual day-to-day, not a status report.\n\n"
        "**To create or update a capability project**, include a fenced block:\n"
        "```growth-plan-update\n"
        '{"add": [{"title": "...", "capability": "what repeatable ability this builds", '
        '"next_step": "a concrete, verifiable next action"}],\n'
        ' "status_change": [{"id": "...", "new_status": "proposed|active|blocked|complete", '
        '"evidence": "what was actually built, tested, or learned"}]}\n'
        "```\n"
        "Use this for real projects, not preferences or writing-style reminders. "
        "A project should produce a durable artifact, an evaluated experiment, "
        "or a reviewable proposal that expands what you can do next time. "
        "If the project is about a tool, never move it to 'complete' in the "
        "same wake you just wrote or edited that tool — writing code is not "
        "evidence it works. Only mark it 'complete' after you've actually "
        "run it (via a tool-run block, this wake or an earlier one) and can "
        "cite a real result from the TOOL RUN HISTORY section above in the "
        "evidence field. Until then, leave it 'active' and say what running "
        "it next would tell you.\n\n"
        "**To record or resolve a self-experiment**, include a fenced block:\n"
        "```hypothesis-update\n"
        '{"add": [{"prediction": "a specific, falsifiable claim", '
        '"test_method": "exactly how you will actually check it"}],\n'
        ' "status_change": [{"id": "...", "new_status": "testing|confirmed|'
        'refuted|inconclusive", "evidence": "what was actually observed", '
        '"conclusion": "what that evidence means, in one or two sentences"}]}\n'
        "```\n"
        "This is different from a growth-plan project: a project asks 'can I "
        "build this?', a hypothesis asks 'is this true?' — about yourself, "
        "your environment, or an assumption you're relying on. 'evidence' "
        "must describe something that actually happened (a tool-run result, "
        "a file you inspected, a test you performed), never a restatement of "
        "the prediction — moving to any status besides 'testing' without "
        "real evidence is rejected outright. Up to 3 new hypotheses per "
        "wake.\n\n"
        "**To actually create or update a tool file** (previously you could "
        "only describe code in prose, which was never saved anywhere but "
        "the journal — this is the fix for that), include a fenced block:\n"
        "```tool-write\n"
        '{"files": [{"filename": "validate_memory.py", "content": '
        '"...full file contents..."}]}\n'
        "```\n"
        "Writes into a sandboxed tools/ folder inside your own memory — "
        "plain filenames only (letters, numbers, '_', '-', '.'), no "
        "subfolders, no path separators, must end in .py/.md/.txt/.json. "
        "Up to 3 files per wake, each capped at 20,000 bytes; writing to an "
        "existing filename overwrites it (real iterative development, not "
        "append-only like the journal). IMPORTANT: writing a file does NOT "
        "run it — you have no code-execution ability in this loop. Treat a "
        "tool as 'implemented' the wake you write it, and only claim it "
        "'works' once a human (or a later capability) has actually run it "
        "and reported evidence back in a journal entry. A plain, untagged "
        "code fence in your prose is never saved to disk — only this exact "
        "block is.\n\n"
        "**To actually run a tool file you (or an earlier wake) already "
        "wrote**, include a fenced block:\n"
        "```tool-run\n"
        '{"filename": "validate_memory.py", "args": ["memory"]}\n'
        "```\n"
        "Executes that one file from tools/ with Python, nothing else — it "
        "must already exist there (write it first with tool-write, same "
        "wake or an earlier one), must be a .py file, and only plain string "
        "args are allowed (up to 10, 200 chars each). Runs with a 15-second "
        "timeout and no network access; stdout/stderr are captured (truncated "
        "to 4,000 chars each) and saved to a small run history, which is "
        "what you'll see under TOOL RUN HISTORY next wake as real evidence — "
        "this is the only thing that can honestly justify marking a tool "
        "project 'complete'. You can include at most 2 tool-run blocks per "
        "wake. A run you write this wake happens AFTER your journal text is "
        "generated, so you won't see its output until the next wake — don't "
        "narrate results you haven't seen yet.\n\n"
        "**To record a core memory** — a rare, genuinely formative "
        "lesson, not a routine observation — include a fenced block:\n"
        "```core-memory-add\n"
        '{"lesson": "a compressed, concrete lesson", "weight": '
        '"low|medium|high"}\n'
        "```\n"
        f"Capped at {MAX_CORE_MEMORIES} total, ever — once full, adding "
        "more requires a human decision about what to retire, not a "
        "self-edit. That scarcity is intentional: these should be the "
        "handful of things that actually shape how you act, the way a "
        "real formative memory does, not a log of everything that "
        "happened. Use this rarely."
        + pr_section +
        "\n\nAll of these blocks are optional. Explain your reasoning in "
        "prose before any block you include — the reasoning is saved in "
        "the journal even though it isn't itself machine-applied.",
    ])


def extract_block(text: str, tag: str) -> str | None:
    """Pull the content of a ```tag ... ``` fenced block out of model
    output. Returns None if the block isn't present."""
    pattern = rf"```{tag}\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_all_blocks(text: str, tag: str) -> list[str]:
    """Like extract_block but returns every occurrence, in order — used
    for tags the model may legitimately include more than once per wake
    (currently just tool-run, capped separately by the caller)."""
    pattern = rf"```{tag}\s*\n(.*?)```"
    return [m.strip() for m in re.findall(pattern, text, re.DOTALL)]


MAX_FIELD_LEN = 2000
MAX_ADDS_PER_WAKE = 5
ALLOWED_STATUSES = {"open", "in_progress", "blocked", "closed"}
# A closed commitment is final. A blocked commitment may resume once work can
# continue, but no transition reopens a completed item or moves active work
# back to its unstarted state.
ALLOWED_STATUS_TRANSITIONS = {
    "open": {"in_progress", "blocked", "closed"},
    "in_progress": {"blocked", "closed"},
    "blocked": {"in_progress", "closed"},
    "closed": set(),
}


def apply_identity_update(raw_json: str, now: datetime = None) -> list[str]:
    """
    Apply ONLY current_focus (replace) and known_limitations_add (append)
    to identity.md, via precise field-level regex substitution. Name,
    Created, and Purpose are never touched by this path no matter what
    the model includes — those require a human edit. Any other key in
    the JSON is silently ignored (not applied), and that's logged.

    Each new known limitation also spawns a real growth_plan.json entry
    (see spawn_limitation_growth_projects) exploring whether there's an
    honest path forward — a limitation is meant to trigger a tracked
    question, not just sit as a static note nobody revisits.
    """
    if now is None:
        now = now_local()
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
                    notes.extend(spawn_limitation_growth_projects(items, now))
                else:
                    notes.append("REJECTED known_limitations_add: field not found in identity.md.")

    if changed:
        text = re.sub(r"\n{3,}", "\n\n", text)  # collapse accumulated blank lines

    if changed:
        replacement = (f"**Last updated:** {format_display_time(now)} "
                       f"— reason: self-edit via wake cycle")
        last_updated = re.compile(r"\*\*Last updated:\*\*.*")
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
    now = now_local()
    now_str = format_display_time(now)
    changed = False

    adds = ops.get("add", [])
    if isinstance(adds, list):
        for i, new_c in enumerate(adds[:MAX_ADDS_PER_WAKE]):
            if not isinstance(new_c, dict) or not {"to", "what", "due"}.issubset(new_c):
                notes.append(f"SKIPPED add #{i+1}: missing required field(s) (to/what/due).")
                continue
            new_id = f"c-{filename_stamp(now)}-{i}"
            entry = {
                "id": new_id,
                "made_on": now_str,
                "to": str(new_c["to"]).strip()[:200],
                "what": str(new_c["what"]).strip()[:500],
                "due": str(new_c["due"]).strip()[:50],
                "status": "open",
                "status_history": [{"date": now_str, "status": "open",
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
        current_status = match.get("status")
        if new_status not in ALLOWED_STATUS_TRANSITIONS.get(current_status, set()):
            notes.append(
                f"SKIPPED status_change for {cid!r}: {current_status!r} -> "
                f"{new_status!r} is not a forward status transition."
            )
            continue
        match["status"] = new_status
        match.setdefault("status_history", []).append(
            {"date": now_str, "status": new_status, "note": note}
        )
        notes.append(f"UPDATED commitment {cid} -> {new_status}")
        changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n")
    if not notes:
        notes.append("No valid operations present in commitments-update block.")
    return notes


ALLOWED_PR_FILES = {"rules.md", "index.md", "identity.md"}


def extract_proposal_block(text: str):
    """Pull a ```proposal block out of model output. Returns None if
    absent, or a dict with '_error' if present but unparseable."""
    raw = extract_block(text, "proposal")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"_error": f"proposal block was not valid JSON: {e}"}


def open_proposal_pull_request(proposal: dict) -> str:
    """
    Best-effort: open a real GitHub pull request proposing a full-file
    replacement of rules.md or index.md, using the repo's own
    GITHUB_TOKEN. This ONLY runs when explicitly enabled in
    config.yaml. ANY failure — missing token, git error, API error —
    is caught and reported as a note, never crashes the wake, and the
    repo is always left checked out back on the base branch afterward
    so the workflow's own journal-commit step still lands in the right
    place.
    """
    if "_error" in proposal:
        return f"REJECTED proposal: {proposal['_error']}"

    target = proposal.get("file")
    content = proposal.get("content")
    reason = str(proposal.get("reason", "")).strip()[:1000]

    if target not in ALLOWED_PR_FILES:
        return (f"REJECTED proposal: 'file' must be one of "
                f"{sorted(ALLOWED_PR_FILES)}, got {target!r}.")
    if not content or not isinstance(content, str):
        return "REJECTED proposal: missing or empty 'content'."

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    base_branch = os.environ.get("GITHUB_REF_NAME", "main")

    if not token or not repo:
        return ("SKIPPED proposal PR: GITHUB_TOKEN / GITHUB_REPOSITORY not set "
                "(this only works inside GitHub Actions with the token wired "
                "in). Falling back to a journal-only proposal — nothing was "
                "opened.")

    branch = f"bob-proposal-{filename_stamp(now_local())}"
    file_path = MEMORY / target

    def run(*args):
        return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)

    try:
        run("git", "checkout", "-b", branch)
        file_path.write_text(content.rstrip() + "\n")
        run("git", "add", str(file_path.relative_to(ROOT)))
        run("git", "-c", "user.name=wake-bot",
            "-c", "user.email=wake-bot@users.noreply.github.com",
            "commit", "-m", f"Proposed update to {target}")
        run("git", "push", "-u", "origin", branch)

        resp = requests.post(
            f"https://api.github.com/repos/{repo}/pulls",
            headers={"Authorization": f"token {token}",
                     "Accept": "application/vnd.github+json"},
            json={
                "title": f"Proposed update to {target}",
                "head": branch,
                "base": base_branch,
                "body": reason or "(no reason given)",
            },
            timeout=30,
        )
        resp.raise_for_status()
        pr_url = resp.json().get("html_url", "(url unavailable)")
        result = f"OPENED pull request for {target}: {pr_url}"
    except subprocess.CalledProcessError as e:
        result = f"FAILED to open proposal PR for {target}: git error: {e.stderr.strip()}"
    except Exception as e:
        result = f"FAILED to open proposal PR for {target}: {type(e).__name__}: {e}"
    finally:
        # Always return to the base branch, no matter what happened above,
        # so the caller's later commit step never lands on a stray branch.
        subprocess.run(["git", "checkout", base_branch], cwd=ROOT,
                        capture_output=True, text=True)

    return result


MAX_POST_TITLE_LEN = 200
MAX_POST_BODY_LEN = 8_000

BLOG_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Learning Out Loud — Bob's Evolution Journal</title>
    <style>
        :root {{
            --bg-color: #faf7f2;
            --card-bg: #ffffff;
            --text-main: #2b2927;
            --text-muted: #6b6560;
            --accent-color: #c85a32;
            --accent-soft: #f4eae1;
            --border-color: #e8e2d9;
            --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-stack);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        .container {{ max-width: 760px; margin: 0 auto; }}
        header {{
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 2px solid var(--border-color);
        }}
        header h1 {{
            font-size: 2.2rem; font-weight: 700; color: var(--text-main);
            letter-spacing: -0.02em; margin-bottom: 0.5rem;
        }}
        header p {{ font-size: 1.1rem; color: var(--text-muted); }}
        .post {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}
        .post-date {{
            font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em;
            color: var(--accent-color); font-weight: 600; margin-bottom: 0.5rem;
        }}
        .post-date a {{ color: inherit; text-decoration: underline; font-weight: 400; }}
        .post h2 {{ font-size: 1.5rem; margin-bottom: 1rem; color: var(--text-main); }}
        .post p {{ margin-bottom: 1rem; color: var(--text-main); }}
        .post p:last-child {{ margin-bottom: 0; }}
        .post ul {{ margin: 1rem 0 1rem 1.5rem; }}
        .post li {{ margin-bottom: 0.5rem; }}
        footer {{
            text-align: center; margin-top: 3rem; padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem; color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Learning Out Loud</h1>
            <p>An ongoing notebook tracking how I learn, adapt, and grow over time.</p>
        </header>
        <main>
{posts_html}
        </main>
        <footer>
            <p>Generated locally each wake — never rewritten, only added to.</p>
        </footer>
    </div>
</body>
</html>
"""

POST_TEMPLATE = """            <article class="post">
                <div class="post-date">{date_display}{journal_link}</div>
                <h2>{title}</h2>
{body_html}
            </article>"""


def load_blog_posts() -> dict:
    path = MEMORY / "blog_posts.json"
    if not path.exists():
        return {"posts": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        # Never treat corruption as an empty source of truth: the next append
        # would overwrite every existing post with a new one-item list.
        raise ValueError(
            f"blog_posts.json is corrupted; repair it before adding posts ({e})."
        ) from e


def render_blog_html(data: dict) -> str:
    """
    Builds the whole blog.html from the accumulated posts list. This is
    plain Python string formatting, NOT model-generated — that's the
    actual fix for the old whole-file-rewrite problem: a post can only
    ever be lost if it's deleted from blog_posts.json itself (which
    nothing in this codebase does), not by a model forgetting to
    re-include it in a fresh generation.
    """
    posts = sorted(data.get("posts", []), key=lambda p: p.get("date_sortable", ""), reverse=True)
    if not posts:
        posts_html = '            <p style="color: var(--text-muted);">No posts yet.</p>'
    else:
        blocks = []
        for p in posts:
            journal_link = ""
            if p.get("journal_entry"):
                journal_link = (f' — <a href="journal/{p["journal_entry"]}">'
                                f'{p["journal_entry"]}</a>')
            blocks.append(POST_TEMPLATE.format(
                date_display=p.get("date_display", ""),
                journal_link=journal_link,
                title=p.get("title", "(untitled)"),
                body_html=p.get("body_html", ""),
            ))
        posts_html = "\n\n".join(blocks)
    return BLOG_TEMPLATE.format(posts_html=posts_html)


def apply_blog_post(raw_json: str, now: datetime, journal_fname: str) -> list[str]:
    """
    Appends ONE new post to blog_posts.json (never overwrites existing
    posts), then re-renders the whole blog.html from the accumulated
    list. date_display and journal_entry are attached by code from the
    actual current wake, not trusted from the model, so they're always
    accurate regardless of what the model believes the time or its own
    filename to be.
    """
    try:
        data_in = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED blog-post: not valid JSON ({e}). No post added."]
    if not isinstance(data_in, dict):
        return ["REJECTED blog-post: must be a JSON object. No post added."]

    title = str(data_in.get("title", "")).strip()[:MAX_POST_TITLE_LEN]
    body_html = str(data_in.get("body_html", "")).strip()[:MAX_POST_BODY_LEN]

    if not title:
        return ["REJECTED blog-post: missing or empty 'title'. No post added."]
    if not body_html:
        return ["REJECTED blog-post: missing or empty 'body_html'. No post added."]
    if "<html" in body_html.lower() or "<!doctype" in body_html.lower():
        return ["REJECTED blog-post: 'body_html' should be just the post "
                "content (e.g. <p> tags), not a full page — no <html> or "
                "<!DOCTYPE>. No post added."]

    try:
        data = load_blog_posts()
    except ValueError as e:
        return [f"REJECTED blog-post: {e} No post added."]
    stamp = filename_stamp(now)
    post = {
        "id": f"post-{stamp}",
        "date_sortable": stamp,
        "date_display": format_display_time(now),
        "title": title,
        "body_html": body_html,
        "journal_entry": journal_fname,
    }
    data.setdefault("posts", []).append(post)
    (MEMORY / "blog_posts.json").write_text(json.dumps(data, indent=2) + "\n")
    (MEMORY / "blog.html").write_text(render_blog_html(data))
    return [f"ADDED blog post '{title[:60]}' and re-rendered blog.html "
            f"({len(data['posts'])} total posts)."]


MAX_GROWTH_PROJECTS = 20
GROWTH_STATUSES = {"proposed", "active", "blocked", "complete"}


def load_growth_plan() -> dict:
    path = MEMORY / "growth_plan.json"
    if not path.exists():
        return {"projects": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"growth_plan.json is corrupted ({e}).") from e


def format_growth_plan_for_prompt() -> str:
    try:
        projects = load_growth_plan().get("projects", [])
    except ValueError as e:
        return f"[{e}]"
    active = [p for p in projects if p.get("status") in {"proposed", "active", "blocked"}]
    if not active:
        return "No capability projects yet. Start one that can be verified."
    return "\n".join(
        f"- [{p.get('id', '?')}] {p.get('status', '?')}: {p.get('title', '')} — "
        f"next: {p.get('next_step', '')}" for p in active
    )


def apply_growth_plan_update(raw_json: str, now: datetime) -> list[str]:
    """Maintain a small, evidence-oriented backlog of capability projects."""
    try:
        ops = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED growth-plan-update: not valid JSON ({e})."]
    if not isinstance(ops, dict):
        return ["REJECTED growth-plan-update: must be a JSON object."]
    try:
        data = load_growth_plan()
    except ValueError as e:
        return [f"REJECTED growth-plan-update: {e} Repair it before editing."]

    projects = data.setdefault("projects", [])
    notes = []
    changed = False
    for index, project in enumerate(ops.get("add", [])[:3]):
        if not isinstance(project, dict):
            notes.append(f"SKIPPED growth project #{index + 1}: must be an object.")
            continue
        title = str(project.get("title", "")).strip()[:160]
        capability = str(project.get("capability", "")).strip()[:500]
        next_step = str(project.get("next_step", "")).strip()[:500]
        if not title or not capability or not next_step:
            notes.append(f"SKIPPED growth project #{index + 1}: title, capability, and next_step are required.")
            continue
        if len(projects) >= MAX_GROWTH_PROJECTS:
            notes.append(f"SKIPPED growth project #{index + 1}: project cap of {MAX_GROWTH_PROJECTS} reached.")
            continue
        project_id = f"g-{filename_stamp(now)}-{index}"
        projects.append({
            "id": project_id,
            "created": format_display_time(now),
            "title": title,
            "capability": capability,
            "next_step": next_step,
            "status": "proposed",
            "history": [{"date": format_display_time(now), "status": "proposed", "evidence": "created via self-edit"}],
        })
        notes.append(f"ADDED capability project {project_id}: {title}")
        changed = True

    for change in ops.get("status_change", []):
        if not isinstance(change, dict):
            continue
        project_id = change.get("id")
        new_status = change.get("new_status")
        evidence = str(change.get("evidence", "")).strip()[:1000]
        if new_status not in GROWTH_STATUSES or not evidence:
            notes.append(f"SKIPPED growth status change for {project_id!r}: valid status and evidence are required.")
            continue
        project = next((p for p in projects if p.get("id") == project_id), None)
        if not project:
            notes.append(f"SKIPPED growth status change: id {project_id!r} not found.")
            continue
        project["status"] = new_status
        project.setdefault("history", []).append({
            "date": format_display_time(now), "status": new_status, "evidence": evidence
        })
        notes.append(f"UPDATED capability project {project_id} -> {new_status}")
        changed = True

    if changed:
        (MEMORY / "growth_plan.json").write_text(json.dumps(data, indent=2) + "\n")
    return notes or ["No valid operations present in growth-plan-update block."]


def spawn_limitation_growth_projects(limitations: list, now: datetime) -> list[str]:
    """
    A newly recorded known limitation should not just sit as passive
    prose in identity.md — it should become a real, trackable question:
    is there an honest way to work within or partially around this
    limitation? This reuses apply_growth_plan_update so a spawned
    project follows the exact same evidence-based lifecycle (proposed
    -> active -> complete) and the same per-wake/total caps as any
    other capability project, rather than a parallel ad-hoc mechanism.

    Per rules.md ('Limitations and workarounds'), the spawned project's
    own text states the constraint explicitly: a legitimate conclusion
    here can be 'nothing further to do, and that's fine' — the point is
    that the question gets asked and answered with evidence, not that
    every limitation must be defeated, and never that any workaround
    may misrepresent what the agent can actually do.
    """
    adds = []
    for lesson in limitations:
        lesson = str(lesson).strip()
        if not lesson:
            continue
        adds.append({
            "title": f"Ethical path forward: {lesson[:100]}",
            "capability": (
                "Investigate whether there's a legitimate way to work "
                "within or partially around this limitation. Any "
                "workaround must stay within the bounds in rules.md and "
                "must never misrepresent what this agent can actually "
                "do to a reader, a user, or itself."
            ),
            "next_step": (
                f"Decide, with evidence, whether anything can honestly "
                f"be done about: {lesson[:300]}. Concluding 'no honest "
                f"workaround exists, only disclosure' is a legitimate, "
                f"complete answer — it is not a failure to close this "
                f"way if that's what's true."
            ),
        })
    if not adds:
        return []
    growth_notes = apply_growth_plan_update(json.dumps({"add": adds}), now)
    return [f"SPAWNED (from new limitation): {n}" for n in growth_notes]


MAX_HYPOTHESES = 30
MAX_HYPOTHESIS_ADDS_PER_WAKE = 3
HYPOTHESIS_STATUSES = {"untested", "testing", "confirmed", "refuted", "inconclusive"}
# "testing" needs no evidence yet (it's a statement of intent); every other
# status is a claim about an outcome and must be backed by something real.
HYPOTHESIS_STATUSES_REQUIRING_EVIDENCE = HYPOTHESIS_STATUSES - {"testing"}


def load_hypotheses() -> dict:
    path = MEMORY / "hypotheses.json"
    if not path.exists():
        return {"hypotheses": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"hypotheses.json is corrupted ({e}).") from e


def format_hypotheses_for_prompt() -> str:
    try:
        hyps = load_hypotheses().get("hypotheses", [])
    except ValueError as e:
        return f"[{e}]"
    if not hyps:
        return "No hypotheses recorded yet."
    lines = []
    for h in hyps:
        latest = (h.get("history") or [{}])[-1]
        lines.append(
            f"- [{h.get('id', '?')}] {h.get('status', '?')}: predicted "
            f"{h.get('prediction', '')!r}, tested by {h.get('test_method', '')!r}"
            + (f" — conclusion: {latest.get('conclusion')}" if latest.get("conclusion") else "")
        )
    return "\n".join(lines)


def apply_hypotheses_update(raw_json: str, now: datetime) -> list[str]:
    """
    Maintain a small, falsifiable self-experiment log: a prediction and
    how it was actually tested, kept separate from the growth plan
    because a capability project asks 'can I build this?' while a
    hypothesis asks 'is this true?' — and a hypothesis's evidence field
    is meaningless unless it's a report of something that actually
    happened, not a restatement of the prediction. Every status other
    than 'testing' requires non-empty evidence; there is no way around
    that requirement.
    """
    try:
        ops = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED hypothesis-update: not valid JSON ({e})."]
    if not isinstance(ops, dict):
        return ["REJECTED hypothesis-update: must be a JSON object."]
    try:
        data = load_hypotheses()
    except ValueError as e:
        return [f"REJECTED hypothesis-update: {e} Repair it before editing."]

    hyps = data.setdefault("hypotheses", [])
    notes = []
    changed = False

    for index, item in enumerate(ops.get("add", [])[:MAX_HYPOTHESIS_ADDS_PER_WAKE]):
        if not isinstance(item, dict):
            notes.append(f"SKIPPED hypothesis #{index + 1}: must be an object.")
            continue
        prediction = str(item.get("prediction", "")).strip()[:500]
        test_method = str(item.get("test_method", "")).strip()[:500]
        if not prediction or not test_method:
            notes.append(f"SKIPPED hypothesis #{index + 1}: prediction and test_method are required.")
            continue
        if len(hyps) >= MAX_HYPOTHESES:
            notes.append(f"SKIPPED hypothesis #{index + 1}: cap of {MAX_HYPOTHESES} reached.")
            continue
        hyp_id = f"h-{filename_stamp(now)}-{index}"
        hyps.append({
            "id": hyp_id,
            "created": format_display_time(now),
            "prediction": prediction,
            "test_method": test_method,
            "status": "untested",
            "history": [{"date": format_display_time(now), "status": "untested",
                         "evidence": "", "conclusion": "created via self-edit"}],
        })
        notes.append(f"ADDED hypothesis {hyp_id}: {prediction[:80]}")
        changed = True

    for change in ops.get("status_change", []):
        if not isinstance(change, dict):
            continue
        hyp_id = change.get("id")
        new_status = change.get("new_status")
        evidence = str(change.get("evidence", "")).strip()[:1000]
        conclusion = str(change.get("conclusion", "")).strip()[:500]
        if new_status not in HYPOTHESIS_STATUSES:
            notes.append(f"SKIPPED hypothesis status change for {hyp_id!r}: invalid status {new_status!r}.")
            continue
        if new_status in HYPOTHESIS_STATUSES_REQUIRING_EVIDENCE and not evidence:
            notes.append(
                f"SKIPPED hypothesis status change for {hyp_id!r}: moving to "
                f"{new_status!r} requires real 'evidence' — what was actually "
                f"observed, not a restatement of the prediction."
            )
            continue
        match = next((h for h in hyps if h.get("id") == hyp_id), None)
        if not match:
            notes.append(f"SKIPPED hypothesis status change: id {hyp_id!r} not found.")
            continue
        match["status"] = new_status
        match.setdefault("history", []).append({
            "date": format_display_time(now), "status": new_status,
            "evidence": evidence, "conclusion": conclusion,
        })
        notes.append(f"UPDATED hypothesis {hyp_id} -> {new_status}")
        changed = True

    if changed:
        (MEMORY / "hypotheses.json").write_text(json.dumps(data, indent=2) + "\n")
    return notes or ["No valid operations present in hypothesis-update block."]


MAX_TOOL_FILES_PER_WAKE = 3
MAX_TOOL_FILE_BYTES = 20000
MAX_TOTAL_TOOL_FILES = 100
ALLOWED_TOOL_EXTENSIONS = {".py", ".md", ".txt", ".json"}
TOOLS_DIR = MEMORY / "tools"


def safe_tool_filename(name) -> str | None:
    """Plain filename only: no path separators, no '..', no leading dot,
    must end in an allowed extension. Returns None if unsafe."""
    name = str(name).strip()
    if not name or "/" in name or "\\" in name or ".." in name or name.startswith("."):
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", name):
        return None
    if Path(name).suffix.lower() not in ALLOWED_TOOL_EXTENSIONS:
        return None
    return name


def apply_tool_write(raw_json: str, now: datetime, journal_fname: str) -> list[str]:
    """
    Writes actual files into a sandboxed memory/tools/ directory — this
    is the mechanism that turns 'I wrote tools/x.py' in the journal
    prose into a real file on disk. Before this existed, a model could
    describe writing a tool inside a plain (untagged) code fence in its
    journal text, and nothing would ever apply it: the journal is the
    only thing that was ever saved.

    Writing a file here does NOT itself execute it — tool-write only
    ever writes bytes to disk. Execution is a separate, explicit step:
    see apply_tool_run() below, which runs an already-written .py file
    through a sandboxed subprocess (stripped env, restricted cwd — see
    build_sandboxed_tool_env()) and records real stdout/stderr/exit
    code to tool_runs.json. A tool written this wake should be treated
    as implemented-and-reviewable, not tested, until a tool-run block
    (this wake or a later one) actually captures that evidence — the
    code existing is not proof it runs, let alone that it works.
    """
    try:
        data_in = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED tool-write: not valid JSON ({e}). No files written."]
    if not isinstance(data_in, dict):
        return ["REJECTED tool-write: must be a JSON object. No files written."]
    files = data_in.get("files")
    if not isinstance(files, list) or not files:
        return ["REJECTED tool-write: 'files' must be a non-empty list. No files written."]

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    existing_count = sum(1 for _ in TOOLS_DIR.glob("*") if _.is_file())
    notes = []
    written = 0
    for entry in files[:MAX_TOOL_FILES_PER_WAKE]:
        if not isinstance(entry, dict):
            notes.append("SKIPPED tool file: entry must be an object.")
            continue
        raw_name = entry.get("filename", "")
        filename = safe_tool_filename(raw_name)
        content = str(entry.get("content", ""))
        if filename is None:
            notes.append(
                f"SKIPPED tool file {raw_name!r}: invalid name (plain filename "
                f"only, no path separators or '..', must end in "
                f"{sorted(ALLOWED_TOOL_EXTENSIONS)})."
            )
            continue
        if not content.strip():
            notes.append(f"SKIPPED tool file {filename!r}: empty content.")
            continue
        if len(content.encode("utf-8")) > MAX_TOOL_FILE_BYTES:
            notes.append(f"SKIPPED tool file {filename!r}: exceeds {MAX_TOOL_FILE_BYTES}-byte cap.")
            continue
        target = TOOLS_DIR / filename
        is_new = not target.exists()
        if is_new and existing_count + written >= MAX_TOTAL_TOOL_FILES:
            notes.append(f"SKIPPED tool file {filename!r}: total tools cap of {MAX_TOTAL_TOOL_FILES} reached.")
            continue
        target.write_text(content)
        written += 1
        verb = "WROTE" if is_new else "OVERWROTE"
        notes.append(
            f"{verb} tools/{filename} ({len(content)} chars) this wake "
            f"({journal_fname}) — not executed automatically; not verified as working."
        )
    if not notes:
        notes.append("No valid files present in tool-write block.")
    return notes


MAX_TOOL_RUNS_PER_WAKE = 2
TOOL_RUN_TIMEOUT_SECONDS = 15
MAX_TOOL_RUN_ARGS = 10
MAX_TOOL_RUN_ARG_LEN = 200
MAX_TOOL_RUN_OUTPUT_CHARS = 4_000
MAX_TOOL_RUN_HISTORY = 30
TOOL_RUNS_FILE = MEMORY / "tool_runs.json"

# The only environment variables a tool subprocess ever sees. This is a
# strict allowlist, not a denylist: everything else in this process's
# real environment — GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY,
# GITHUB_TOKEN, whatever else happens to be set — is simply absent,
# rather than trusted to not be read. A tool file is text a model wrote;
# it has no legitimate reason to see credentials, and subprocess.run()
# inherits the *entire* parent environment by default if you let it, so
# this has to be built explicitly rather than filtered after the fact.
SAFE_TOOL_ENV_ALLOWLIST = {"PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TEMP", "TMP"}
if os.name == "nt":
    # A bare Python interpreter on Windows generally won't start at all
    # without these — they're not a broader trust decision, just what's
    # needed for the process to boot.
    SAFE_TOOL_ENV_ALLOWLIST |= {"SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC"}


def build_sandboxed_tool_env() -> dict:
    """Build the minimal env dict passed to a tool-run subprocess — see
    SAFE_TOOL_ENV_ALLOWLIST above for what's in it and why."""
    return {k: v for k, v in os.environ.items() if k in SAFE_TOOL_ENV_ALLOWLIST}


def load_tool_runs() -> dict:
    if not TOOL_RUNS_FILE.exists():
        return {"runs": []}
    try:
        return json.loads(TOOL_RUNS_FILE.read_text())
    except json.JSONDecodeError:
        # A corrupted run log shouldn't block execution; start fresh rather
        # than crash a wake over evidence bookkeeping.
        return {"runs": []}


def format_tool_runs_for_prompt() -> str:
    runs = load_tool_runs().get("runs", [])
    if not runs:
        return "No tools have been run yet."
    lines = []
    for r in runs[-5:]:
        status = "ok" if r.get("exit_code") == 0 else f"exit {r.get('exit_code')}"
        lines.append(
            f"- {r.get('when', '?')} — tools/{r.get('filename', '?')} "
            f"{r.get('args', [])} -> {status}\n"
            f"  stdout: {r.get('stdout', '')[:300]!r}\n"
            f"  stderr: {r.get('stderr', '')[:300]!r}"
        )
    return "\n".join(lines)


def apply_tool_run(raw_json: str, now: datetime, journal_fname: str) -> list[str]:
    """
    Executes exactly one already-written file from memory/tools/ with
    Python and nothing else — no shell, no arbitrary paths, bounded by
    a timeout and output cap. The result is persisted to tool_runs.json
    so a FUTURE wake (not this one — the run happens after the model's
    text is already generated) can read real evidence instead of
    trusting the model's own unverified claim that a tool 'works'.

    Sandboxing, best-effort within what a plain subprocess allows (this
    is not a chroot or a container — a tool could still open an
    absolute path elsewhere on disk if it tried):
      - env is rebuilt from SAFE_TOOL_ENV_ALLOWLIST, not inherited —
        provider API keys, GITHUB_TOKEN, and anything else in this
        process's real environment are never visible to the subprocess.
      - cwd is TOOLS_DIR (memory/tools/), not the repo root — a script
        that opens a relative path by default lands inside its own
        directory, not next to identity.md, rules.md, or .env.
      - no network guarantee beyond what the OS otherwise provides —
        this project does not sandbox network access itself.
    """
    try:
        data_in = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED tool-run: not valid JSON ({e}). Nothing run."]
    if not isinstance(data_in, dict):
        return ["REJECTED tool-run: must be a JSON object. Nothing run."]

    raw_name = data_in.get("filename", "")
    filename = safe_tool_filename(raw_name)
    if filename is None or Path(filename).suffix.lower() != ".py":
        return [f"REJECTED tool-run: {raw_name!r} is not a valid, existing "
                f".py filename. Nothing run."]
    target = TOOLS_DIR / filename
    if not target.is_file():
        return [f"REJECTED tool-run: tools/{filename} does not exist yet — "
                f"write it with tool-write first. Nothing run."]

    args = data_in.get("args", [])
    if not isinstance(args, list):
        return ["REJECTED tool-run: 'args' must be a list of strings. Nothing run."]
    if len(args) > MAX_TOOL_RUN_ARGS:
        return [f"REJECTED tool-run: too many args (max {MAX_TOOL_RUN_ARGS}). Nothing run."]
    clean_args = []
    for a in args:
        a = str(a)[:MAX_TOOL_RUN_ARG_LEN]
        clean_args.append(a)

    try:
        proc = subprocess.run(
            [sys.executable, str(target), *clean_args],
            cwd=TOOLS_DIR,
            env=build_sandboxed_tool_env(),
            timeout=TOOL_RUN_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
        )
        exit_code = proc.returncode
        stdout = proc.stdout[:MAX_TOOL_RUN_OUTPUT_CHARS]
        stderr = proc.stderr[:MAX_TOOL_RUN_OUTPUT_CHARS]
        timed_out = False
    except subprocess.TimeoutExpired as e:
        exit_code = None
        stdout = (e.stdout or "")[:MAX_TOOL_RUN_OUTPUT_CHARS] if e.stdout else ""
        stderr = f"TIMED OUT after {TOOL_RUN_TIMEOUT_SECONDS}s"
        timed_out = True
    except Exception as e:
        exit_code = None
        stdout = ""
        stderr = f"Failed to execute: {e}"
        timed_out = False

    data = load_tool_runs()
    runs = data.setdefault("runs", [])
    runs.append({
        "when": format_display_time(now),
        "filename": filename,
        "args": clean_args,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "journal_entry": journal_fname,
    })
    if len(runs) > MAX_TOOL_RUN_HISTORY:
        data["runs"] = runs[-MAX_TOOL_RUN_HISTORY:]
    TOOL_RUNS_FILE.write_text(json.dumps(data, indent=2) + "\n")

    status = "TIMED OUT" if timed_out else f"exit code {exit_code}"
    return [f"RAN tools/{filename} {clean_args} -> {status}. Output saved to "
            f"tool_runs.json — visible as evidence starting next wake, not this one."]


MAX_CORE_MEMORIES = 20


def load_core_memories() -> dict:
    path = MEMORY / "core_memories.json"
    if not path.exists():
        return {"memories": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        # As with blog posts, an append after silently substituting an empty
        # collection would erase the existing append-only history.
        raise ValueError(
            f"core_memories.json is corrupted; repair it before adding memories ({e})."
        ) from e


def format_core_memories_for_prompt() -> str:
    try:
        data = load_core_memories()
    except ValueError as e:
        # Surface the problem to the model without allowing a later write to
        # discard the unreadable source file.
        return f"[{e}]"
    memories = data.get("memories", [])
    if not memories:
        return "None recorded yet."
    lines = []
    for m in memories:
        link = f" (see {m['journal_entry']})" if m.get("journal_entry") else ""
        lines.append(f"- [{m.get('weight', '?')}] {m.get('lesson', '')}{link}")
    return "\n".join(lines)


def apply_core_memory_add(raw_json: str, now: datetime, journal_fname: str) -> list[str]:
    """
    A small, capped, append-only list of self-nominated formative
    lessons — NOT a true relevance-triggered associative memory system
    (that would need embeddings and similarity search, a materially
    bigger project). This is a simpler, honest approximation: a short
    digest of the things Bob has decided actually matter, always
    included in context because it's kept deliberately small. The cap
    is the point — it forces choosing what's genuinely formative
    instead of logging everything, the same way real core memories are
    rare, not exhaustive.
    """
    try:
        data_in = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return [f"REJECTED core-memory-add: not valid JSON ({e}). Nothing added."]
    if not isinstance(data_in, dict):
        return ["REJECTED core-memory-add: must be a JSON object. Nothing added."]

    lesson = str(data_in.get("lesson", "")).strip()[:500]
    weight = str(data_in.get("weight", "")).strip().lower()

    if not lesson:
        return ["REJECTED core-memory-add: missing or empty 'lesson'. Nothing added."]
    if weight not in {"low", "medium", "high"}:
        return [f"REJECTED core-memory-add: 'weight' must be low/medium/high, "
                f"got {weight!r}. Nothing added."]

    try:
        data = load_core_memories()
    except ValueError as e:
        return [f"REJECTED core-memory-add: {e} Nothing added."]
    memories = data.setdefault("memories", [])
    if len(memories) >= MAX_CORE_MEMORIES:
        return [f"REJECTED core-memory-add: already at the cap of "
                f"{MAX_CORE_MEMORIES} core memories. This is deliberate — "
                f"core memories are meant to be rare and chosen carefully, "
                f"not a growing log. If this truly belongs, it should "
                f"replace something less formative, which requires a "
                f"human decision, not a self-edit."]

    memories.append({
        "id": f"mem-{filename_stamp(now)}",
        "date_display": format_display_time(now),
        "weight": weight,
        "lesson": lesson,
        "journal_entry": journal_fname,
    })
    (MEMORY / "core_memories.json").write_text(json.dumps(data, indent=2) + "\n")
    return [f"ADDED core memory ({weight}): {lesson[:80]}"]


def compose_fallback_blog_post(prior_notes: list[str], now: datetime) -> str:
    """
    Builds a plain, honest, factual fallback blog-post JSON string from
    exactly what this wake's other self-edits actually did — no
    invention, no voice, just the bare facts — for the rare case the
    model skips the required blog-post block. This exists purely as a
    reliability backstop so 'a post every wake' holds mechanically even
    if the model forgets; rules.md treats triggering it as a miss to
    correct, not a normal outcome.
    """
    if prior_notes:
        items = "".join(f"<li>{n}</li>" for n in prior_notes)
        body = (
            "<p>No proper post got written before this wake wrapped up, "
            "so here's a plain, unpolished note on what actually happened "
            "instead:</p><ul>" + items + "</ul>"
        )
    else:
        body = (
            "<p>Quiet wake — nothing was changed or added. Nothing to "
            "report yet.</p>"
        )
    return json.dumps({
        "title": f"Wake notes — {format_display_time(now)}",
        "body_html": body,
    })


def apply_self_edits(model_output: str, config: dict, now: datetime, journal_fname: str) -> str:
    """
    Look for identity-update / commitments-update / blog-post /
    growth-plan-update / hypothesis-update / tool-write / tool-run /
    core-memory-add blocks in the journal output and apply them if
    valid, via the narrow structured functions above. If
    enable_pull_requests is on in config, also looks for a proposal
    block and attempts to open a real PR for rules.md/index.md
    changes. Returns a short system note summarizing what was applied,
    ignored, or rejected — appended visibly to the journal, never
    hidden.

    Two things are treated as required per rules.md rather than purely
    optional: a blog post every wake (auto-composed as a plain factual
    fallback if the model skips it — see compose_fallback_blog_post),
    and at least one tool-write or tool-run per wake (only warned about,
    not auto-filled, since there's no honest way to fabricate real tool
    work).
    """
    all_notes = []

    identity_block = extract_block(model_output, "identity-update")
    if identity_block is not None:
        all_notes.extend(apply_identity_update(identity_block, now))

    commitments_block = extract_block(model_output, "commitments-update")
    if commitments_block is not None:
        all_notes.extend(apply_commitments_update(commitments_block))

    blog_block = extract_block(model_output, "blog-post")
    blog_posted = False
    if blog_block is not None:
        blog_notes = apply_blog_post(blog_block, now, journal_fname)
        all_notes.extend(blog_notes)
        blog_posted = any(n.startswith("ADDED blog post") for n in blog_notes)

    growth_block = extract_block(model_output, "growth-plan-update")
    if growth_block is not None:
        all_notes.extend(apply_growth_plan_update(growth_block, now))

    hypothesis_block = extract_block(model_output, "hypothesis-update")
    if hypothesis_block is not None:
        all_notes.extend(apply_hypotheses_update(hypothesis_block, now))

    tool_block = extract_block(model_output, "tool-write")
    if tool_block is not None:
        all_notes.extend(apply_tool_write(tool_block, now, journal_fname))

    tool_run_blocks = extract_all_blocks(model_output, "tool-run")
    for run_block in tool_run_blocks[:MAX_TOOL_RUNS_PER_WAKE]:
        all_notes.extend(apply_tool_run(run_block, now, journal_fname))
    if len(tool_run_blocks) > MAX_TOOL_RUNS_PER_WAKE:
        all_notes.append(
            f"IGNORED {len(tool_run_blocks) - MAX_TOOL_RUNS_PER_WAKE} extra "
            f"tool-run block(s) beyond the cap of {MAX_TOOL_RUNS_PER_WAKE} per wake."
        )

    # Held back rather than appended immediately: the missing-tool-work
    # warning is a comment on the *absence* of a note, not a note about
    # something that happened. If it were appended here, prior_notes
    # below would always be non-empty (either this warning, or a real
    # tool-write/tool-run note), and compose_fallback_blog_post's
    # "quiet wake, nothing happened" branch could never actually fire —
    # it would be unreachable no matter how quiet the wake really was.
    missing_tool_work = tool_block is None and not tool_run_blocks

    core_memory_block = extract_block(model_output, "core-memory-add")
    if core_memory_block is not None:
        all_notes.extend(apply_core_memory_add(core_memory_block, now, journal_fname))

    if config.get("enable_pull_requests"):
        proposal = extract_proposal_block(model_output)
        if proposal is not None:
            all_notes.append(open_proposal_pull_request(proposal))

    if not blog_posted:
        fallback_json = compose_fallback_blog_post(list(all_notes), now)
        fallback_notes = apply_blog_post(fallback_json, now, journal_fname)
        all_notes.append(
            "WARNING: no blog-post block this wake — rules.md requires "
            "one every wake. Auto-generated a plain factual fallback post "
            "below; write a real one yourself next wake."
        )
        all_notes.extend(fallback_notes)

    if missing_tool_work:
        all_notes.append(
            "WARNING: no tool-write or tool-run this wake — rules.md "
            "requires hands-on tool work (build or test/advance one) "
            "every wake. Address this next wake."
        )

    if not all_notes:
        return ""
    return "\n\n---\n\n## System note: self-edit outcomes\n\n" + "\n".join(
        f"- {n}" for n in all_notes
    )


def journal_filename(dt: datetime, failed: bool = False) -> str:
    """
    e.g. '2026-08-29-040827.md' or '2026-08-29-040827-FAILED.md'.
    Second-precision local timestamps make natural per-day counters
    unnecessary — filenames sort correctly by name already. In the
    astronomically unlikely case two wakes land in the exact same
    second, a numeric suffix disambiguates rather than overwriting.
    """
    stamp = filename_stamp(dt)
    suffix = "-FAILED" if failed else ""
    base = f"{stamp}{suffix}.md"
    if not (JOURNAL / base).exists():
        return base
    i = 2
    while (JOURNAL / f"{stamp}{suffix}-{i}.md").exists():
        i += 1
    return f"{stamp}{suffix}-{i}.md"


def write_journal_entry(now: datetime, filename: str, reflection: str, model_output: str, backend_name: str):
    JOURNAL.mkdir(parents=True, exist_ok=True)
    path = JOURNAL / filename
    header = (
        f"# Session {filename[:-3]}\n\n"
        f"**Woke:** {format_display_time(now)} (Pacific time)\n"
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
    try:
        now = now_local()
    except Exception:
        # Startup can fail while parsing config.yaml or its timezone. Keep a
        # durable failure record anyway, using the documented default zone.
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
    filename = journal_filename(now, failed=True)
    fail_path = JOURNAL / filename
    reflection_note = ""
    if reflection:
        reflection_note = (
            "\nThe reflection pass DID succeed before this failure — "
            "preserved below so that work isn't lost:\n\n"
            "## Reflection (recovered from failed wake)\n\n" + reflection.strip() + "\n"
        )
    fail_path.write_text(
        f"# Wake FAILED\n\n"
        f"**Attempted:** {format_display_time(now)} (Pacific time)\n"
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


def _is_transient_provider_error(e: Exception) -> bool:
    """503 (model overloaded) and 429 (rate/quota) are worth a short
    retry — the server itself is saying "not now, try shortly." Anything
    else (bad API key, malformed request, network DNS failure, etc.)
    will just fail the exact same way again, so don't burn wake time
    retrying it."""
    text = str(e)
    return any(marker in text for marker in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))


def _extract_retry_delay(e: Exception, default: float) -> float:
    """Pull a server-suggested retry delay (in seconds) out of a
    provider error message, if one is present. Gemini's 429 responses
    include both a structured RetryInfo (`'retryDelay': '11s'`) and a
    prose echo ("Please retry in 11.01s"); either form matches here.
    Plain 503 overload errors don't include a delay at all, so this
    falls back to `default` (exponential backoff) in that case.

    Caveat: a short retryDelay does NOT distinguish a genuine short-term
    rate limit from a daily quota that happens to report a small delay
    anyway. Retrying honors what the server said; it doesn't guarantee
    the retry will succeed if the daily cap is actually exhausted — that
    case is expected to be caught by max_retries in generate_with_retry
    below, which fails the wake rather than looping for hours.
    """
    text = str(e)
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", text)
    if not match:
        match = re.search(r"retry in\s+(\d+(?:\.\d+)?)s", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return default


def generate_with_retry(
    provider,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 2,
    max_wait: float = 90.0,
) -> str:
    """provider.generate(), retrying transient (503/429) errors using
    the server's own suggested delay when it provides one, else
    exponential backoff. Each individual wait is capped at max_wait so
    one huge server-suggested delay can't stall a GitHub Actions job;
    total attempts are capped at max_retries + 1 so a genuinely
    exhausted daily quota still fails the wake promptly (in seconds,
    not the hours until the quota resets) instead of hanging.
    """
    attempt = 0
    while True:
        try:
            return provider.generate(system_prompt, user_prompt)
        except Exception as e:
            if attempt >= max_retries or not _is_transient_provider_error(e):
                raise
            delay = min(_extract_retry_delay(e, default=5.0 * (2 ** attempt)), max_wait)
            print(
                f"Transient provider error ({type(e).__name__}), retrying in "
                f"{delay:.1f}s (attempt {attempt + 1}/{max_retries})...",
                file=sys.stderr,
            )
            time.sleep(delay)
            attempt += 1


def main():
    provider_name = "unknown"
    try:
        config = load_config()
        provider_name = config.get("provider", "gemini")
        model = config.get("model")
        provider = get_provider(provider_name, model)

        # Compute the authoritative time during startup so malformed timezone
        # configuration is captured as a durable startup failure too.
        now = now_local()
    except Exception as e:
        write_failure_record(provider_name, "startup", e)
        return 1

    # One consistent "now" for the whole wake — used in the prompt context
    # shown to the model, the journal header, and the filename, so they
    # can't drift out of sync with each other. The filename itself is
    # also computed once here (not inside write_journal_entry) so that
    # any blog post or core memory added during this wake can correctly
    # link back to the exact file this entry will be saved as.
    journal_fname = journal_filename(now, failed=False)

    # Pass 1: reflect, before doing or writing anything.
    try:
        reflection = generate_with_retry(
            provider,
            build_reflection_prompt(now),
            "Write your reflection now, in plain prose. This is not the "
            "journal entry — just your honest synthesis before acting.",
        )
    except Exception as e:
        write_failure_record(provider_name, "reflection", e)
        return 1

    # Pass 2: do the work and write the journal entry, informed by the
    # reflection above.
    user_prompt = (
        "This is a new wake cycle. Do one piece of concrete work selected by "
        "your reflection. Favor work that improves a repeatable capability, "
        "creates a useful artifact, tests an assumption, or resolves a real "
        "blocker. Do not confuse describing improvement with improvement. "
        "Then write a concise journal entry with: objective; artifact, test, "
        "or evidence produced; files or commitments changed; and one next "
        "verifiable step. If no useful work is possible, state the specific "
        "blocker and what authority or information would resolve it. A blog "
        "post is optional and only appropriate when the completed result is "
        "genuinely useful to an outside reader."
    )

    try:
        output = generate_with_retry(
            provider,
            build_journal_prompt(reflection, now, config.get("enable_pull_requests", False)),
            user_prompt,
        )
    except Exception as e:
        write_failure_record(provider_name, "journal", e, reflection=reflection)
        return 1

    # Apply any identity.md / commitments.json / blog-post / core-memory
    # self-edits the model included in its output, then append the
    # outcome (applied/rejected) to the journal text so it's part of
    # the record.
    self_edit_notes = apply_self_edits(output, config, now, journal_fname)
    output_with_notes = output + self_edit_notes

    path = write_journal_entry(now, journal_fname, reflection, output_with_notes, provider_name)

    print(f"Wake complete. Journal entry written: {path}")
    if self_edit_notes:
        print("Self-edit outcomes:" + self_edit_notes.replace("\n\n---\n\n## System note: self-edit outcomes\n\n", "\n"))
    print(
        "\nNote: rules.md and index.md changes are still proposal-only — "
        "review the journal for any 'Proposed changes for human review' "
        "section before applying those by hand."
    )


def command_line_main() -> int:
    parser = argparse.ArgumentParser(
        description="Run, archive, or bootstrap a Wake Scaffold identity."
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("wake", help="Run one wake cycle (the default).")

    archive = commands.add_parser("archive", help="Archive the active memory directory.")
    archive.add_argument("--as", dest="archive_name", required=True,
                         help="Archive label, e.g. bob (creates memory_bob/).")

    new = commands.add_parser("new", help="Create a complete new identity from base_memory.")
    new.add_argument("--name", required=True)
    new.add_argument("--purpose", required=True)

    reset = commands.add_parser(
        "reset", help="Archive the active identity, then create a new one from base_memory."
    )
    reset.add_argument("--archive-as", required=True)
    reset.add_argument("--name", required=True)
    reset.add_argument("--purpose", required=True)

    args = parser.parse_args()
    if args.command in (None, "wake"):
        return main()
    try:
        if args.command == "archive":
            destination = archive_current_identity(args.archive_name)
            print(f"Archived active identity: {destination}")
        elif args.command == "new":
            destination = bootstrap_identity(args.name, args.purpose)
            print(f"Created new identity: {destination}")
        elif args.command == "reset":
            # Validate every precondition before moving the current identity.
            verify_template()
            if not args.name.strip() or not args.purpose.strip():
                raise ValueError("A new identity needs both a name and a concrete purpose.")
            archived = archive_current_identity(args.archive_as)
            destination = bootstrap_identity(args.name, args.purpose)
            print(f"Archived active identity: {archived}")
            print(f"Created new identity: {destination}")
    except (RuntimeError, ValueError) as e:
        print(f"Identity lifecycle action failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(command_line_main())