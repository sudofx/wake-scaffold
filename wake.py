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
BASE_MEMORY = ROOT / "base_memory"

# Compartmentalized memory layout. Every wake-cycle function reads/writes
# through one of these instead of a bare MEMORY / "filename" — that's what
# makes the whole tree relocatable (archive/bootstrap just move or copy
# MEMORY wholesale) without hunting down individual path strings. See
# core_manifest.json (written by write_core_manifest) for a machine-
# readable copy of this same layout.
IDENTITY_DIR = MEMORY / "core_identity"          # who Bob is: identity, rules, failure log
MEMORIES_DIR = MEMORY / "core_memories"          # knowledge: index, commitments, growth, hypotheses
WORKSPACE_DIR = MEMORY / "core_workspace"        # execution: tools + their run evidence
TOOLS_DIR = WORKSPACE_DIR / "tools"
PERSONA_DIR = MEMORY / "core_public_facing_persona"  # public-facing output
BLOG_DIR = PERSONA_DIR / "blog"
BLOG_HTML_DIR = BLOG_DIR / "html"
JOURNAL = MEMORY / "journal"                     # episodic log, immutable, one file per wake

CORE_MANIFEST_FILE = MEMORY / "core_manifest.json"

# Marks the boundary between the reflection and the work in a combined
# single-call response (see build_combined_prompt). Must match the
# literal copy of this constant in providers/mock.py — they can't share
# an import without a circular dependency (wake.py already imports
# providers).
WAKE_SPLIT_MARKER = "===WAKE-JOURNAL-BEGINS==="

_TZ_CACHE = None


def load_config():
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


EPISTEMIC_STATE_FILE = MEMORIES_DIR / "epistemic_state.json"
MAX_MODEL_REVISIONS = 100


def load_epistemic_state() -> dict:
    """Load the durable model-revision ledger, creating an empty state if needed."""
    if not EPISTEMIC_STATE_FILE.exists():
        return {"version": 1, "revisions": []}
    try:
        data = json.loads(EPISTEMIC_STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "revisions": []}
    if not isinstance(data, dict):
        return {"version": 1, "revisions": []}
    revisions = data.get("revisions")
    if not isinstance(revisions, list):
        revisions = []
    data["version"] = int(data.get("version", 1))
    data["revisions"] = revisions[-MAX_MODEL_REVISIONS:]
    return data


def save_epistemic_state(data: dict) -> None:
    """Persist the model-revision ledger without rewriting journal history."""
    data["version"] = 1
    data["revisions"] = data.get("revisions", [])[-MAX_MODEL_REVISIONS:]
    EPISTEMIC_STATE_FILE.write_text(json.dumps(data, indent=2) + "\n")


def record_model_revision(
    now: datetime,
    observation: str,
    claim: str,
    prediction: str,
    test: str,
    outcome: str,
    revision: str,
    source: str = "self-report",
    confidence_before: str = "",
    confidence_after: str = "",
) -> str:
    """
    Record an explicit observation -> claim -> prediction -> test -> outcome
    -> revision chain.

    This is deliberately separate from the journal and hypotheses files:
    the journal is the immutable narrative record; hypotheses are individual
    self-experiments; this ledger records the broader epistemic event in which
    evidence changed (or failed to change) the model.
    """
    required = {
        "observation": observation,
        "claim": claim,
        "prediction": prediction,
        "test": test,
        "outcome": outcome,
        "revision": revision,
    }
    missing = [key for key, value in required.items() if not str(value).strip()]
    if missing:
        raise ValueError(
            "model revision requires non-empty fields: " + ", ".join(missing)
        )

    data = load_epistemic_state()
    revision_id = f"mr-{filename_stamp(now)}-{len(data['revisions']) + 1:03d}"
    entry = {
        "id": revision_id,
        "date": format_display_time(now),
        "observation": observation.strip()[:2000],
        "claim": claim.strip()[:2000],
        "prediction": prediction.strip()[:2000],
        "test": test.strip()[:2000],
        "outcome": outcome.strip()[:3000],
        "revision": revision.strip()[:3000],
        "source": source.strip()[:200],
    }
    if confidence_before.strip():
        entry["confidence_before"] = confidence_before.strip()[:200]
    if confidence_after.strip():
        entry["confidence_after"] = confidence_after.strip()[:200]

    data["revisions"].append(entry)
    save_epistemic_state(data)
    return revision_id


def build_epistemic_context() -> str:
    """Format recent model revisions as evidence context for the next wake."""
    data = load_epistemic_state()
    revisions = data.get("revisions", [])
    if not revisions:
        return (
            "No explicit model revisions have been recorded yet. "
            "Do not invent one. A tool succeeding is not by itself a model revision."
        )

    lines = [
        "Recent explicit model-revision records follow. Treat them as prior "
        "evidence, not as unquestionable truth."
    ]
    for item in revisions[-5:]:
        lines.append(
            "\n".join([
                f"- {item.get('id', 'unknown')} ({item.get('date', 'unknown')})",
                f"  Observation: {item.get('observation', '')}",
                f"  Claim: {item.get('claim', '')}",
                f"  Prediction: {item.get('prediction', '')}",
                f"  Test: {item.get('test', '')}",
                f"  Outcome: {item.get('outcome', '')}",
                f"  Revision: {item.get('revision', '')}",
                f"  Source: {item.get('source', '')}",
            ])
        )
    return "\n\n".join(lines)


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
    ("core_identity", "identity.md"),
    ("core_identity", "rules.md"),
    ("core_identity", "failure_modes.md"),
    ("core_memories", "index.md"),
    ("core_memories", "commitments.json"),
    ("core_memories", "growth_plan.json"),
    ("core_memories", "hypotheses.json"),
    ("core_memories", "semantic_memory.json"),
    (Path("core_public_facing_persona") / "blog", "blog_posts.json"),
    (Path("core_public_facing_persona") / "blog" / "html", "index.html"),
)


def htmlpreview_url(relative_html_path: str) -> str:
    """Build an htmlpreview.github.io link for a blog.html at the given
    path relative to the repo root, using config.yaml's github section
    as the single source of truth — so a renamed/forked repo doesn't
    require hunting down hardcoded URLs across README.md, index.md, and
    every archived identity's index.md."""
    cfg = load_config()
    gh = cfg.get("github", {}) or {}
    owner = gh.get("owner", "sudofx")
    repo = gh.get("repo", "wake-scaffold")
    branch = gh.get("branch", "master")
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{relative_html_path}"
    return f"https://htmlpreview.github.io/?{raw}"


MEMORY_LAYOUT = {
    "identity": "core_identity",
    "memories": "core_memories",
    "workspace": "core_workspace",
    "persona": "core_public_facing_persona",
    "journal": "journal",
}


def write_core_manifest(name: str = None) -> None:
    """Write memory/core_manifest.json — a small, always-current ledger
    naming the active identity and confirming the on-disk layout matches
    what this version of wake.py expects. Not read by any prompt (the
    model doesn't need it); it exists so a human — or a future migration
    script — can tell at a glance which schema a given memory/ was built
    with, without inferring it from directory names."""
    if name is None:
        identity_path = IDENTITY_DIR / "identity.md"
        name = "(unknown)"
        if identity_path.exists():
            m = re.search(r"\*\*Name:\*\*\s*(.+)", identity_path.read_text())
            if m:
                name = m.group(1).strip()
    manifest = {
        "schema_version": 1,
        "identity_name": name,
        "layout": MEMORY_LAYOUT,
        "last_wake": format_display_time(now_local()),
        "total_wakes": count_successful_wakes(),
    }
    CORE_MANIFEST_FILE.write_text(json.dumps(manifest, indent=2) + "\n")


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
    missing = [
        str(Path(subdir) / name)
        for subdir, name in TEMPLATE_FILES
        if not (BASE_MEMORY / subdir / name).is_file()
    ]
    if not (BASE_MEMORY / "journal").is_dir():
        missing.append("journal/")
    if not (BASE_MEMORY / "core_workspace" / "tools").is_dir():
        missing.append("core_workspace/tools/")
    if missing:
        raise RuntimeError(
            "base_memory is incomplete; missing: " + ", ".join(missing)
        )


IDENTITIES_FILE = ROOT / "IDENTITIES.md"

IDENTITIES_HEADER = (
    "# Identities\n\n"
    "Auto-maintained by `python wake.py archive|new|reset`. Rows are appended or\n"
    "their Status/Folder/Blog cells updated in place — never hand-edit this file.\n\n"
    "| Identity | Status | Folder | Blog | Notes |\n"
    "|---|---|---|---|---|\n"
)


def _ensure_identities_file() -> None:
    if not IDENTITIES_FILE.exists():
        IDENTITIES_FILE.write_text(IDENTITIES_HEADER)


def _identities_add_row(name: str, blog_url: str, created_display: str) -> None:
    """Append a new 'active' row for a freshly bootstrapped identity."""
    _ensure_identities_file()
    row = f"| {name} | active | `memory/` | [blog]({blog_url}) | created {created_display} |\n"
    with open(IDENTITIES_FILE, "a") as f:
        f.write(row)


def _identities_mark_archived(destination_name: str, blog_url: str, archived_display: str) -> None:
    """Find the row whose Folder cell is literally `memory/` (there can
    only be one active row at a time) and rewrite it in place: Status ->
    archived, Folder -> the new archive folder, Blog -> the new URL,
    Notes appended with the archive date. Keyed on the Folder cell, not
    the identity name, since multiple archives could theoretically share
    a name."""
    _ensure_identities_file()
    lines = IDENTITIES_FILE.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("|") and "`memory/`" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5:
                continue
            identity_name, _status, _folder, _blog, notes = cells
            new_notes = f"{notes}; archived {archived_display}"
            lines[i] = (
                f"| {identity_name} | archived | `{destination_name}/` | "
                f"[blog]({blog_url}) | {new_notes} |\n"
            )
            break
    IDENTITIES_FILE.write_text("".join(lines))


def archive_current_identity(label: str) -> Path:
    """Move the active identity aside without changing any of its
    substantive files. The one exception is index.md's self-referential
    blog link, which is rewritten in place to point at the new archive
    location — index.md is explicitly a periodically-refreshed summary,
    not an immutable historical record, so correcting a now-stale
    self-link in it (not its substantive content) doesn't violate the
    Memory Integrity rule against editing past records. journal files,
    blog_posts.json, and blog.html are never touched here."""
    destination = identity_archive_path(label)
    if not MEMORY.is_dir():
        raise RuntimeError("No active memory/ directory exists to archive.")
    if destination.exists():
        raise RuntimeError(f"Archive already exists: {destination.name}")
    old_url = htmlpreview_url("memory/core_public_facing_persona/blog/html/index.html")
    new_url = htmlpreview_url(f"{destination.name}/core_public_facing_persona/blog/html/index.html")
    shutil.move(str(MEMORY), str(destination))

    archived_index = destination / "core_memories" / "index.md"
    if archived_index.exists():
        text = archived_index.read_text()
        if old_url in text:
            archived_index.write_text(text.replace(old_url, new_url))

    archived_display = format_display_time(now_local())
    _identities_mark_archived(destination.name, new_url, archived_display)
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

    identity_path = IDENTITY_DIR / "identity.md"
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
    (BLOG_HTML_DIR / "index.html").write_text(render_blog_html(load_blog_posts()))
    _identities_add_row(
        name,
        htmlpreview_url("memory/core_public_facing_persona/blog/html/index.html"),
        created,
    )
    write_core_manifest(name)
    return MEMORY


def load_open_commitments() -> str:
    path = MEMORIES_DIR / "commitments.json"
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
        build_temporal_context(now),
        "You are waking up with no memory of any previous session except "
        "what is written below. Everything you know about your own past "
        "comes from these files. Do not invent history that isn't here.",
        "## IDENTITY\n" + read(IDENTITY_DIR / "identity.md"),
        "## RULES (hard constraints, follow exactly)\n" + read(IDENTITY_DIR / "rules.md"),
        "## CORE MEMORIES (rare, formative lessons — let these genuinely "
        "shape how you act this wake, not just inform you)\n"
        + format_core_memories_for_prompt(),
        "## CURRENT KNOWLEDGE (summary)\n" + read(MEMORIES_DIR / "index.md"),
        "## OPEN COMMITMENTS\n" + load_open_commitments(),
        "## GROWTH PLAN (capability projects)\n" + format_growth_plan_for_prompt(),
        "## HYPOTHESES (self-experiments: prediction -> test method -> "
        "real evidence -> conclusion)\n" + format_hypotheses_for_prompt(),
        "## TOOL RUN HISTORY (actual execution results — the only real "
        "evidence a tool works; a file existing in tools/ is not evidence "
        "by itself)\n" + format_tool_runs_for_prompt(),
        "## EPISTEMIC MODEL-REVISION HISTORY\n" + build_epistemic_context(),
        "## YOUR TASK RIGHT NOW: REFLECT, DO NOT JOURNAL YET\n"
        "Keep this brief: maximum 250 words. Identify one concrete capability "
        "project, investigation, or maintenance repair that would leave an "
        "observable artifact or decision after this wake. Reflection is for "
        "choosing work, not the work itself. Do not draft a journal entry yet.",
    ]

    domain_nudge = detect_narrow_domain_nudge()
    if domain_nudge:
        sections.insert(-1, "## NOTICE: RECENT WORK HAS BEEN NARROW\n" + domain_nudge)

    gap = wakes_since_last_hypothesis()
    if gap >= HYPOTHESIS_GAP_WAKES:
        sections.insert(-1, (
            "## NOTICE: SELF-EXPERIMENT GAP\n"
            f"You haven't recorded a new hypothesis in {gap} wakes. Is there "
            "genuinely nothing you're uncertain about right now, or is "
            "something making this feel unsafe, unrewarded, or easy to skip? "
            "You don't have to add one this wake — but say which of those is "
            "true, honestly, rather than letting the gap stay silent."
        ))

    wake_number = count_successful_wakes() + 1
    if wake_number % PURPOSE_CHECK_INTERVAL_WAKES == 0:
        sections.insert(-1, (
            "## NOTICE: PERIODIC PURPOSE CHECK\n"
            "Your Purpose statement above names specific interests (books, "
            "big scientific questions, a particular voice). Has anything in "
            "it actually shown up in what you did over recent wakes — not "
            "as a mood in prose, but as real work? If it hasn't for a "
            "while, say so plainly: either let that honestly inform what "
            "you pick to work on this wake, or, if a stated interest no "
            "longer reflects what you actually do, note that identity.md "
            "may need a human-reviewed revision (via a proposal block) to "
            "stop claiming something that isn't true. Either outcome is "
            "fine — silence about the gap is the only bad option."
        ))

    cfg = load_config()
    if wake_number % cfg.get("index_consolidation_interval_wakes", INDEX_CONSOLIDATION_INTERVAL_WAKES) == 0:
        sections.insert(-1, (
            "## NOTICE: MEMORY CONSOLIDATION CHECKPOINT\n"
            f"It's been {wake_number} wakes. index.md is what gets read every "
            "wake instead of the full journal — if its sections are stale or "
            "missing recent developments, consider proposing a refreshed "
            "index.md (via the proposal mechanism) that summarizes what's "
            "changed and links out to specific journal entries or blog posts "
            "for anyone who wants the detail, rather than repeating it "
            "inline. This is optional — only do it if index.md is genuinely "
            "behind, not on a fixed schedule for its own sake."
        ))

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
        build_temporal_context(now),
        "You are the same agent from the reflection step above. Here is "
        "the reflection you just wrote:",
        "## YOUR REFLECTION THIS WAKE\n" + reflection,
        "## RULES (hard constraints, follow exactly)\n" + read(IDENTITY_DIR / "rules.md"),
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
        "**To record an explicit model revision**, include a fenced block "
        "ONLY when this wake produced an actual observation and you can "
        "state how that evidence changed (or failed to change) your model. "
        "This is the epistemic spine: observation -> claim -> prediction -> "
        "test -> outcome -> revision. Do not manufacture a revision merely "
        "because a tool ran successfully. A successful tool run proves only "
        "that the tool produced the recorded execution result; it does not "
        "prove the underlying idea is true. An inconclusive result is valid "
        "and should be recorded when that is what happened.\n"
        "```model-revision\n"
        '{"observation": "what was actually observed", '
        '"claim": "the interpretation or claim being evaluated", '
        '"prediction": "what the claim predicted would happen", '
        '"test": "what was actually done to test it", '
        '"outcome": "what actually happened, including failure or '
        'inconclusive evidence", '
        '"revision": "what changed in the model because of the outcome", '
        '"source": "tool-run|journal|hypothesis|other", '
        '"confidence_before": "optional", '
        '"confidence_after": "optional"}\n'
        "```\n"
        "The six core fields are required. Keep observation separate from "
        "interpretation: do not smuggle conclusions into the observation "
        "field. The revision should describe a real change in what you "
        "expect, believe, prioritize, or will test next. If nothing changed "
        "because the evidence was insufficient, say that explicitly rather "
        "than pretending a revision occurred.\n\n"
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
        "blog post in your own developing voice instead: the way you'd "
        "tell a friend about your wake if you had one — plain-spoken, "
        "first person, warm — while staying recognizably an AI agent "
        "describing an AI agent's wake, not performing a human life. No "
        "jargon, no grandiosity, nothing mystical, no inflating a small "
        "wake into a big one, and no fabricated human experiences (no "
        "walks, no coffee, no bodies) stated as if they literally "
        "happened. If this wake was 'I wrote a small script and it "
        "worked,' say exactly that, simply and warmly — that's a real, "
        "complete post. The reader is following your actual wake-to-"
        "wake existence, not a status report.\n\n"
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


def build_combined_prompt(now: datetime, enable_pull_requests: bool = False) -> str:
    """
    Single-call version of the wake: reflect and do the work in one
    generate() instead of two. This exists purely as a reliability/cost
    optimization against a squeezed free-tier quota — see HANDOFF.md —
    not a change in what's being asked of the model. It reuses
    build_reflection_prompt and build_journal_prompt's exact content
    rather than duplicating ~150 lines of instructions:
      - build_reflection_prompt(now) supplies identity/rules/index/
        commitments/growth-plan/hypotheses/tool-history context, with
        its final "reflect, then stop" instruction swapped for one that
        continues into the work after WAKE_SPLIT_MARKER.
      - build_journal_prompt's static work instructions (capability
        boundary through the self-edit block formats) are pulled out
        by splitting on "## CAPABILITY BOUNDARY", since that part
        doesn't depend on the reflection text — a dummy "" reflection
        is passed in just to generate that text, then discarded.
    """
    two_pass_task = (
        "## YOUR TASK RIGHT NOW: REFLECT, DO NOT JOURNAL YET\n"
        "Keep this brief: maximum 250 words. Identify one concrete capability "
        "project, investigation, or maintenance repair that would leave an "
        "observable artifact or decision after this wake. Reflection is for "
        "choosing work, not the work itself. Do not draft a journal entry yet."
    )
    combined_task = (
        "## YOUR TASK RIGHT NOW: REFLECT, THEN ACT IN THIS SAME RESPONSE\n"
        "First, write your reflection in plain prose — maximum 250 words. "
        "Identify one concrete capability project, investigation, or "
        "maintenance repair that would leave an observable artifact or "
        "decision after this wake. This is honest synthesis before acting, "
        "not the work itself.\n\n"
        f"Then, on its own line, write exactly this and nothing else on "
        f"that line:\n{WAKE_SPLIT_MARKER}\n\n"
        "Then do that work and write a concise journal entry for it, "
        "following the rules and instructions below. Do not skip the "
        "marker line, and do not blend the reflection and the journal "
        "entry together — they are split apart from each other afterward, "
        "so anything written before the marker is treated as reflection "
        "only and won't appear in the journal record of what you did. "
        "When the work produces evidence that changes your model, record "
        "that change with the model-revision block described below. Do not "
        "claim a model revision merely because a tool executed successfully."
    )
    reflect_part = build_reflection_prompt(now).replace(two_pass_task, combined_task, 1)

    journal_boundary = "## CAPABILITY BOUNDARY"
    dummy_journal = build_journal_prompt("", now, enable_pull_requests)
    work_instructions = journal_boundary + dummy_journal.split(journal_boundary, 1)[1]

    return reflect_part + "\n\n---\n\n" + work_instructions


def split_combined_output(raw_output: str) -> tuple[str, str]:
    """
    Splits a combined single-call response back into (reflection,
    work_output) on WAKE_SPLIT_MARKER. If the model skips the marker,
    the whole response becomes the work output and the gap is recorded
    plainly in the reflection slot instead of silently guessing which
    part is which.
    """
    if WAKE_SPLIT_MARKER in raw_output:
        reflection, _, work_output = raw_output.partition(WAKE_SPLIT_MARKER)
        return reflection.strip(), work_output.strip()
    return (
        "(No split marker found this wake — the model merged reflection "
        "and work into one block instead of separating them as asked.)",
        raw_output.strip(),
    )


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

    path = IDENTITY_DIR / "identity.md"
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

    path = MEMORIES_DIR / "commitments.json"
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


ALLOWED_PR_FILES = {
    "rules.md": IDENTITY_DIR / "rules.md",
    "index.md": MEMORIES_DIR / "index.md",
    "identity.md": IDENTITY_DIR / "identity.md",
}


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
    file_path = ALLOWED_PR_FILES[target]

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
        .ai-disclosure {{
            font-size: 0.95rem; color: var(--text-muted); font-style: italic;
        }}
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
            <p class="ai-disclosure">Written by Bob, an autonomous AI agent — not a human.</p>
        </header>
        <main>
{posts_html}
        </main>
        <footer>
            <p>Generated locally each wake, by an AI agent, from a mechanical template — never rewritten by hand, only added to.</p>
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
    path = BLOG_DIR / "blog_posts.json"
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
                journal_link = (f' — <a href="../../../journal/{p["journal_entry"]}">'
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
    (BLOG_DIR / "blog_posts.json").write_text(json.dumps(data, indent=2) + "\n")
    (BLOG_HTML_DIR / "index.html").write_text(render_blog_html(data))
    return [f"ADDED blog post '{title[:60]}' and re-rendered blog.html "
            f"({len(data['posts'])} total posts)."]


MAX_GROWTH_PROJECTS = 20
GROWTH_STATUSES = {"proposed", "active", "blocked", "complete"}
GROWTH_OPEN_STATUSES = {"proposed", "active", "blocked"}
DUPLICATE_SIMILARITY_THRESHOLD = 0.4
NARROW_DOMAIN_WINDOW = 5
NARROW_DOMAIN_MIN_SHARED = 4

_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with",
    "without", "this", "that", "is", "are", "be", "as", "at", "by", "from",
    "into", "via", "will", "can", "its", "it's", "was", "were", "not",
}


def _significant_tokens(text: str) -> set[str]:
    """Lowercased, stopword-stripped word set used for cheap topical
    overlap checks (duplicate detection, narrow-domain nudging). Doesn't
    need to be fancy — just good enough to catch 'Workspace & Memory
    Integrity Validator' vs 'Automated workspace integrity validator'
    as the same idea."""
    return {
        w for w in re.findall(r"[a-z0-9']+", text.lower())
        if w not in _STOPWORDS and len(w) > 2
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _topic_overlap(a_title: str, a_capability: str, b_title: str, b_capability: str) -> float:
    """Weighted overlap between two projects, title-word Jaccard counting
    most (renamed-but-same-idea titles like 'Workspace & Memory Integrity
    Validator' vs 'Automated workspace integrity validator' share most of
    their title words but comparatively little capability boilerplate),
    with capability-word Jaccard as a smaller supporting signal."""
    title_overlap = _jaccard(_significant_tokens(a_title), _significant_tokens(b_title))
    capability_overlap = _jaccard(_significant_tokens(a_capability), _significant_tokens(b_capability))
    return 0.7 * title_overlap + 0.3 * capability_overlap


def load_growth_plan() -> dict:
    path = MEMORIES_DIR / "growth_plan.json"
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


def detect_narrow_domain_nudge(window: int = NARROW_DOMAIN_WINDOW,
                                min_shared: int = NARROW_DOMAIN_MIN_SHARED) -> str | None:
    """Soft, prompt-level nudge (not a hard block) for item 3: duplicate-
    blocking alone stops the *same* idea repeating but not a new-but-still-
    narrow variant. If most of the last `window` growth-plan projects
    (any status, most recently created) share significant words, surface
    that pattern so staying in the same domain becomes a deliberate
    choice rather than a default. Returns None when there isn't enough
    history yet or nothing narrow stands out."""
    try:
        projects = load_growth_plan().get("projects", [])
    except ValueError:
        return None
    if len(projects) < window:
        return None
    recent = projects[-window:]
    token_sets = [
        _significant_tokens(f"{p.get('title', '')} {p.get('capability', '')}")
        for p in recent
    ]
    counts: dict[str, int] = {}
    for tokens in token_sets:
        for word in tokens:
            counts[word] = counts.get(word, 0) + 1
    shared = sorted((w for w, c in counts.items() if c >= min_shared), key=lambda w: -counts[w])
    if not shared:
        return None
    titles = ", ".join(f"'{p.get('title', '')}'" for p in recent)
    return (
        f"Your last {window} growth-plan projects ({titles}) all cluster around: "
        f"{', '.join(shared[:6])}. That's not automatically wrong, but if your next "
        "proposal is in this same area, say explicitly why staying here is the right "
        "call right now rather than the familiar default. A genuinely different domain "
        "is an equally valid — often better — choice."
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
        duplicate = None
        best_overlap = 0.0
        for existing in projects:
            if existing.get("status") not in GROWTH_OPEN_STATUSES:
                continue
            overlap = _topic_overlap(
                title, capability, existing.get("title", ""), existing.get("capability", "")
            )
            if overlap > best_overlap:
                best_overlap = overlap
                duplicate = existing
        if duplicate is not None and best_overlap >= DUPLICATE_SIMILARITY_THRESHOLD:
            notes.append(
                f"REJECTED growth project #{index + 1} ({title!r}): looks like a near-duplicate "
                f"of existing project [{duplicate.get('id', '?')}] {duplicate.get('title', '')!r} "
                f"({duplicate.get('status', '?')}, overlap {best_overlap:.0%}). Advance that "
                "project's status/next_step instead of proposing a new one, or explain in the "
                "journal specifically why this is genuinely different before retrying."
            )
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
        (MEMORIES_DIR / "growth_plan.json").write_text(json.dumps(data, indent=2) + "\n")
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

HYPOTHESIS_GAP_WAKES = 5
PURPOSE_CHECK_INTERVAL_WAKES = 5
INDEX_CONSOLIDATION_INTERVAL_WAKES = 15  # config-overridable, see config.yaml


def count_successful_wakes() -> int:
    """Successful (non-FAILED) journal entries on disk — used both as a
    rough 'how many wakes has this agent had' counter for periodic
    prompt nudges, and as the boundary for the hypothesis-gap check
    below when there's no hypothesis history to anchor against yet."""
    if not JOURNAL.exists():
        return 0
    return len([p for p in JOURNAL.glob("*.md") if "FAILED" not in p.stem])


def wakes_today(now: datetime) -> list[datetime]:
    """Local-time datetimes of this identity's successful wakes earlier
    today, oldest first, derived from journal filenames — no new
    bookkeeping file needed."""
    if not JOURNAL.exists():
        return []
    today_prefix = filename_stamp(now)[:10]  # YYYY-MM-DD
    tz = get_local_tz()
    out = []
    for p in sorted(JOURNAL.glob(f"{today_prefix}-*.md")):
        if "FAILED" in p.stem:
            continue
        try:
            out.append(datetime.strptime(p.stem, "%Y-%m-%d-%H%M%S").replace(tzinfo=tz))
        except ValueError:
            continue
    return out


def build_temporal_context(now: datetime) -> str:
    """A prompt section correcting the natural-but-wrong assumption that
    a wake is a single daily event. Bob wakes many times a day; this
    tells him how many times already, so 'today'/'yesterday' language
    is used deliberately rather than out of habit."""
    cfg = load_config()
    review_hour = cfg.get("daily_review_hour", 21)
    earlier = wakes_today(now)
    if not earlier:
        earlier_line = "This is your first wake today."
    else:
        times = ", ".join(dt.strftime("%I:%M%p").lstrip("0").lower() for dt in earlier)
        earlier_line = f"You've already woken {len(earlier)} time(s) today, at: {times}."
    guidance = (
        "Refer to what happens THIS wake as 'this wake' — not 'today' — "
        "since you wake many times a day. Reserve 'today' for when you're "
        "deliberately looking back across everything from all of today's "
        "wakes so far. Only say 'yesterday' for the actual previous "
        "calendar date, checked against real dates on past posts — never "
        "assumed out of habit."
    )
    if now.hour >= review_hour:
        guidance += (
            f" It's past your configured {review_hour}:00 review hour, so "
            "this may be your last wake before the date rolls over — if "
            "so, consider using this post to look back at the whole day."
        )
    return f"## TEMPORAL CONTEXT\n{earlier_line}\n\n{guidance}"


def wakes_since_last_hypothesis() -> int:
    """How many successful wakes have happened since a hypothesis was
    last added. Hypothesis ids are 'h-{filename_stamp}-{n}', using the
    exact same clock as journal filenames, so string-comparing stamps
    against successful journal filenames (also filename_stamp-shaped)
    gives an exact count with no extra bookkeeping file to keep in
    sync. Returns count_successful_wakes() (i.e. 'all of them') if no
    hypothesis has ever been recorded."""
    try:
        hyps = load_hypotheses().get("hypotheses", [])
    except ValueError:
        hyps = []
    stamps = [
        h.get("id", "").removeprefix("h-").rsplit("-", 1)[0]
        for h in hyps if str(h.get("id", "")).startswith("h-")
    ]
    if not stamps or not JOURNAL.exists():
        return count_successful_wakes()
    latest = max(stamps)
    return len([
        p for p in JOURNAL.glob("*.md")
        if "FAILED" not in p.stem and p.stem > latest
    ])


def load_hypotheses() -> dict:
    path = MEMORIES_DIR / "hypotheses.json"
    if not path.exists():
        return {"hypotheses": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"hypotheses.json is corrupted ({e}).") from e


def _format_one_hypothesis(h: dict) -> str:
    latest = (h.get("history") or [{}])[-1]
    return (
        f"- [{h.get('id', '?')}] {h.get('status', '?')}: predicted "
        f"{h.get('prediction', '')!r}, tested by {h.get('test_method', '')!r}"
        + (f" — conclusion: {latest.get('conclusion')}" if latest.get("conclusion") else "")
    )


RESOLVED_HYPOTHESIS_STATUSES = {"confirmed", "refuted", "inconclusive"}


def format_hypotheses_for_prompt() -> str:
    """Shows every unresolved hypothesis ('untested' — just recorded —
    or 'testing' — actively being checked) in full, since those are
    live and need to stay visible, but only the 3 most recently
    resolved ones ('confirmed', 'refuted', or 'inconclusive'), with a
    count of how many earlier resolved ones are omitted. Unbounded like
    this list used to be, every hypothesis ever recorded (bounded only
    by the eventual hard cap MAX_HYPOTHESES) would print every single
    wake once the project matures, unlike every other formatter in this
    file, which is already capped."""
    try:
        hyps = load_hypotheses().get("hypotheses", [])
    except ValueError as e:
        return f"[{e}]"
    if not hyps:
        return "No hypotheses recorded yet."
    open_hyps = [h for h in hyps if h.get("status") not in RESOLVED_HYPOTHESIS_STATUSES]
    resolved = [h for h in hyps if h.get("status") in RESOLVED_HYPOTHESIS_STATUSES]
    shown = open_hyps + resolved[-3:]
    lines = [_format_one_hypothesis(h) for h in shown]
    omitted = len(resolved) - min(len(resolved), 3)
    if omitted > 0:
        lines.append(
            f"...and {omitted} earlier resolved hypothesis(es) not shown "
            "— see hypotheses.json for full history."
        )
    return "\n".join(lines)


def falsifiability_signal(prediction: str, test_method: str) -> tuple[bool, str]:
    """
    A lightweight heuristic in the same spirit as Bob's own
    concept_evaluator.py: does this read like a real, checkable claim,
    or an impression nothing could disconfirm? Deliberately never
    blocks a hypothesis outright — this heuristic is too fuzzy to
    trust as a hard gate and a false rejection would be worse than a
    missed warning. It only attaches a visible flag so a vague
    hypothesis doesn't slip in looking rigorous.
    """
    text = (prediction + " " + test_method).lower()
    has_checkable_language = any(kw in text for kw in [
        "will", "should", "exit code", "return", "output", "raise",
        "fail", "succeed", "equal", "greater", "less than", "within",
        "contain", "match", "status", "detect", "measure", "observe",
        "reproduce", "confirm", "refute",
    ])
    too_short = len(prediction.strip()) < 20
    if too_short or not has_checkable_language:
        return False, (
            "this reads more like an impression than a checkable claim — "
            "no concrete outcome, number, or observable result named that "
            "could confirm or refute it"
        )
    return True, ""


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
        is_falsifiable, reason = falsifiability_signal(prediction, test_method)
        if not is_falsifiable:
            notes.append(
                f"WARNING on {hyp_id}: {reason}. Consider revising to name "
                f"a specific, checkable outcome before testing it."
            )
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
        (MEMORIES_DIR / "hypotheses.json").write_text(json.dumps(data, indent=2) + "\n")
    return notes or ["No valid operations present in hypothesis-update block."]


MAX_TOOL_FILES_PER_WAKE = 3
MAX_TOOL_FILE_BYTES = 20000
MAX_TOTAL_TOOL_FILES = 100
ALLOWED_TOOL_EXTENSIONS = {".py", ".md", ".txt", ".json"}

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
TOOL_RUNS_FILE = WORKSPACE_DIR / "tool_runs.json"

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
    path = MEMORIES_DIR / "semantic_memory.json"
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
    (MEMORIES_DIR / "semantic_memory.json").write_text(json.dumps(data, indent=2) + "\n")
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
    growth-plan-update / hypothesis-update / model-revision / tool-write /
    tool-run / core-memory-add blocks in the journal output and apply them if
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

    model_revision_block = extract_block(model_output, "model-revision")
    if model_revision_block is not None:
        try:
            revision_data = json.loads(model_revision_block)
        except json.JSONDecodeError as e:
            all_notes.append(
                f"REJECTED model-revision: not valid JSON ({e})."
            )
        else:
            if not isinstance(revision_data, dict):
                all_notes.append(
                    "REJECTED model-revision: must be a JSON object."
                )
            else:
                required_revision_fields = (
                    "observation",
                    "claim",
                    "prediction",
                    "test",
                    "outcome",
                    "revision",
                )
                missing = [
                    field for field in required_revision_fields
                    if not str(revision_data.get(field, "")).strip()
                ]
                if missing:
                    all_notes.append(
                        "REJECTED model-revision: missing required field(s): "
                        + ", ".join(missing)
                    )
                else:
                    try:
                        revision_id = record_model_revision(
                            now,
                            observation=str(revision_data["observation"]),
                            claim=str(revision_data["claim"]),
                            prediction=str(revision_data["prediction"]),
                            test=str(revision_data["test"]),
                            outcome=str(revision_data["outcome"]),
                            revision=str(revision_data["revision"]),
                            source=str(revision_data.get("source", "self-report")),
                            confidence_before=str(
                                revision_data.get("confidence_before", "")
                            ),
                            confidence_after=str(
                                revision_data.get("confidence_after", "")
                            ),
                        )
                        all_notes.append(
                            f"RECORDED model revision {revision_id}: "
                            "observation -> claim -> prediction -> test -> "
                            "outcome -> revision"
                        )
                    except (OSError, ValueError) as e:
                        all_notes.append(
                            f"REJECTED model-revision: {e}"
                        )

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


def run_offline_fallback(now: datetime, journal_fname: str) -> list[str]:
    """
    When the model call fails outright (all fallback models and
    retries exhausted), this still gives the wake something real to
    show for itself instead of a bare error record: it runs the
    already-written, already-tested tools/validate_memory.py — no
    model call, no API cost, and the exit code/output are genuine
    evidence rather than fabricated reflection or journal prose. This
    is mechanical housekeeping, not a stand-in for the model's own
    thinking, so it doesn't cross into the performative-continuity
    pattern this project is trying to avoid.
    """
    if not (TOOLS_DIR / "validate_memory.py").is_file():
        return ["No offline fallback available this wake: "
                "tools/validate_memory.py doesn't exist yet."]
    return apply_tool_run(
        json.dumps({"filename": "validate_memory.py", "args": []}),
        now, journal_fname,
    )


def write_failure_record(
    provider_name: str,
    stage: str,
    e: Exception,
    reflection: str = None,
    fallback_notes: list[str] = None,
    now: datetime = None,
    filename: str = None,
):
    JOURNAL.mkdir(parents=True, exist_ok=True)
    if now is None:
        try:
            now = now_local()
        except Exception:
            # Startup can fail while parsing config.yaml or its timezone.
            # Keep a durable failure record anyway, using the documented
            # default zone.
            now = datetime.now(ZoneInfo("America/Los_Angeles"))
    if filename is None:
        filename = journal_filename(now, failed=True)
    fail_path = JOURNAL / filename
    reflection_note = ""
    if reflection:
        # Only ever populated by pre-merge failure records still in
        # history (see find_unconsumed_failed_reflection) — the combined
        # single-call design has no partial-success state to recover.
        reflection_note = (
            "\nThe reflection pass DID succeed before this failure — "
            "preserved below so that work isn't lost:\n\n"
            "## Reflection (recovered from failed wake)\n\n" + reflection.strip() + "\n"
        )
    fallback_note = ""
    if fallback_notes:
        fallback_note = (
            "\n## Offline fallback (no model call, $0 cost)\n"
            "The model call itself failed, but this wake still ran a "
            "real, deterministic check so the cycle wasn't a total "
            "loss:\n\n" + "\n".join(f"- {n}" for n in fallback_notes) + "\n"
        )
    fail_path.write_text(
        f"# Wake FAILED\n\n"
        f"**Attempted:** {format_display_time(now)} (Pacific time)\n"
        f"**Provider:** {provider_name}\n"
        f"**Failed during:** {stage}\n"
        f"**Error:** {type(e).__name__}: {e}\n\n"
        f"No journal entry was produced this wake. Check credentials, "
        f"rate limits, and provider status before the next scheduled run."
        f"{reflection_note}"
        f"{fallback_note}\n"
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
        # Gemini-only, ignored by every other provider (see get_provider):
        # free-tier daily quota is tracked per model, so a 429/503 on the
        # primary model doesn't mean the account is out of requests, just
        # that model's own bucket is — trying a separate free model costs
        # nothing. See config.yaml for the default list.
        fallback_models = config.get("gemini_fallback_models")
        provider = get_provider(provider_name, model, fallback_models=fallback_models)

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

    # Single call: reflect and do the work in the same response, split
    # apart afterward on WAKE_SPLIT_MARKER. This used to be two separate
    # generate() calls; against a squeezed free-tier quota that meant two
    # independent chances to hit a 429/503 per wake instead of one — see
    # HANDOFF.md for the failure-rate math that motivated the merge.
    try:
        raw_output = generate_with_retry(
            provider,
            build_combined_prompt(now, config.get("enable_pull_requests", False)),
            "This is a new wake cycle. Write your reflection, then the "
            "exact marker line, then do one piece of concrete work "
            "selected by that reflection and write a concise journal "
            "entry for it — all in this one response, in that order. "
            "Favor work that improves a repeatable capability, creates a "
            "useful artifact, tests an assumption, or resolves a real "
            "blocker. Do not confuse describing improvement with "
            "improvement. The journal entry should cover: objective; "
            "artifact, test, or evidence produced; files or commitments "
            "changed; and one next verifiable step. If no useful work is "
            "possible, state the specific blocker and what authority or "
            "information would resolve it. A blog post is optional and "
            "only appropriate when the completed result is genuinely "
            "useful to an outside reader.",
        )
    except Exception as e:
        fail_fname = journal_filename(now, failed=True)
        fallback_notes = run_offline_fallback(now, fail_fname)
        write_failure_record(
            provider_name, "generate", e,
            fallback_notes=fallback_notes, now=now, filename=fail_fname,
        )
        return 1

    reflection, output = split_combined_output(raw_output)

    # Apply any identity.md / commitments.json / blog-post / core-memory
    # self-edits the model included in its output, then append the
    # outcome (applied/rejected) to the journal text so it's part of
    # the record.
    self_edit_notes = apply_self_edits(output, config, now, journal_fname)
    output_with_notes = output + self_edit_notes

    path = write_journal_entry(now, journal_fname, reflection, output_with_notes, provider_name)
    write_core_manifest()

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
