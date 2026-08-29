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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yaml

from providers import get_provider

ROOT = Path(__file__).parent
MEMORY = ROOT / "memory"
JOURNAL = MEMORY / "journal"

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


def build_reflection_prompt(now: datetime) -> str:
    """
    The synthesis pass. This is NOT the journal entry — it's private
    thinking that happens first, and gets folded into the journal
    afterward as a labeled section so the reasoning stays visible and
    auditable, not hidden.
    """
    return "\n\n---\n\n".join([
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
            "'file' must be exactly 'rules.md' or 'index.md'. 'content' "
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
        "**To add a new post to your blog** (a plain local page, not "
        "hosted or public), include a fenced block with JUST that "
        "post's title and content — never the whole page, the code "
        "builds the page shell and adds your post to it automatically:\n"
        "```blog-post\n"
        '{"title": "...", "body_html": "<p>...</p><p>...</p>"}\n'
        "```\n"
        "This ADDS a post — it never replaces or removes earlier ones, "
        "so don't try to regenerate the whole blog from scratch or "
        "re-paste old posts; the code keeps every post that's ever "
        "been added automatically, most recent first, each one linked "
        "to the journal entry that created it. Only include this when "
        "you have something genuinely worth posting, not every wake. "
        "'body_html' is just the post content (paragraphs, lists, "
        "etc.), capped at 8,000 characters — no <html> or <!DOCTYPE>, "
        "just the fragment. You can link to other past journal entries "
        "inline in your prose if relevant, e.g. "
        '<a href="journal/2026-08-28-025254.md">that day</a>.\n\n'
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
        replacement = (f"**Last updated:** {format_display_time(now_local())} "
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


ALLOWED_PR_FILES = {"rules.md", "index.md"}


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
    except json.JSONDecodeError:
        return {"posts": []}  # corrupted -> treat as empty rather than crash


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

    data = load_blog_posts()
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


MAX_CORE_MEMORIES = 20


def load_core_memories() -> dict:
    path = MEMORY / "core_memories.json"
    if not path.exists():
        return {"memories": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"memories": []}


def format_core_memories_for_prompt() -> str:
    data = load_core_memories()
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

    data = load_core_memories()
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


def apply_self_edits(model_output: str, config: dict, now: datetime, journal_fname: str) -> str:
    """
    Look for identity-update / commitments-update / blog-post /
    core-memory-add blocks in the journal output and apply them if
    valid, via the narrow structured functions above. If
    enable_pull_requests is on in config, also looks for a proposal
    block and attempts to open a real PR for rules.md/index.md
    changes. Returns a short system note summarizing what was applied,
    ignored, or rejected — appended visibly to the journal, never
    hidden.
    """
    all_notes = []

    identity_block = extract_block(model_output, "identity-update")
    if identity_block is not None:
        all_notes.extend(apply_identity_update(identity_block))

    commitments_block = extract_block(model_output, "commitments-update")
    if commitments_block is not None:
        all_notes.extend(apply_commitments_update(commitments_block))

    blog_block = extract_block(model_output, "blog-post")
    if blog_block is not None:
        all_notes.extend(apply_blog_post(blog_block, now, journal_fname))

    core_memory_block = extract_block(model_output, "core-memory-add")
    if core_memory_block is not None:
        all_notes.extend(apply_core_memory_add(core_memory_block, now, journal_fname))

    if config.get("enable_pull_requests"):
        proposal = extract_proposal_block(model_output)
        if proposal is not None:
            all_notes.append(open_proposal_pull_request(proposal))

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
    now = now_local()
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


def main():
    config = load_config()
    provider_name = config.get("provider", "gemini")
    model = config.get("model")

    provider = get_provider(provider_name, model)

    # One consistent "now" for the whole wake — used in the prompt context
    # shown to the model, the journal header, and the filename, so they
    # can't drift out of sync with each other. The filename itself is
    # also computed once here (not inside write_journal_entry) so that
    # any blog post or core memory added during this wake can correctly
    # link back to the exact file this entry will be saved as.
    now = now_local()
    journal_fname = journal_filename(now, failed=False)

    # Pass 1: reflect, before doing or writing anything.
    try:
        reflection = provider.generate(
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
        output = provider.generate(
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


if __name__ == "__main__":
    sys.exit(main())