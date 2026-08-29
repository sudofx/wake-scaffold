#!/usr/bin/env python3
"""
One-time migration: renames existing journal files from the old
'<date>-NNNN.md' / 'FAILED-<isodate>.md' naming scheme to the new
local-time scheme ('<date>-<time>.md' / '<date>-<time>-FAILED.md').

This ONLY renames files — it never edits their contents. Old entries
keep their original internal text exactly as written (including
whatever timestamp format was recorded at the time), which respects
this project's own append-only / never-edit-a-past-entry rule. Only
the filename changes, derived by parsing each file's own recorded UTC
timestamp and converting it to local time using the same timezone
wake.py uses (see config.yaml).

Usage:
    python scripts/migrate_journal_filenames.py --dry-run   # preview only
    python scripts/migrate_journal_filenames.py              # actually rename

After running for real, remember to 'git add -A' and commit — renames
show up as a delete+add unless git's rename detection notices the
content is unchanged (it usually does, but 'git add -A' either way
gets everything staged correctly).
"""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import wake  # reuse get_local_tz/filename_stamp so this matches the live code exactly

JOURNAL = Path(__file__).parent.parent / "memory" / "journal"

OLD_SUCCESS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}\.md$")
OLD_FAILED_RE = re.compile(r"^FAILED-\d{4}-\d{2}-\d{2}T\d{6}\.md$")
WOKE_LINE_RE = re.compile(r"\*\*Woke:\*\*\s*(\S+)")
ATTEMPTED_LINE_RE = re.compile(r"\*\*Attempted:\*\*\s*(\S+)")


def parse_utc_iso(text: str):
    m = WOKE_LINE_RE.search(text) or ATTEMPTED_LINE_RE.search(text)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1))
    except ValueError:
        return None


def new_filename_for(dt_utc: datetime, failed: bool) -> str:
    local_dt = dt_utc.astimezone(wake.get_local_tz())
    stamp = wake.filename_stamp(local_dt)
    return f"{stamp}{'-FAILED' if failed else ''}.md"


def main():
    dry_run = "--dry-run" in sys.argv
    if not JOURNAL.exists():
        print("No memory/journal directory found.")
        return

    renames = []
    for path in sorted(JOURNAL.iterdir()):
        if not path.name.endswith(".md"):
            continue
        is_old_failed = OLD_FAILED_RE.match(path.name) is not None
        is_old_success = OLD_SUCCESS_RE.match(path.name) is not None
        if not (is_old_failed or is_old_success):
            continue  # already new-scheme, or unrecognized — leave alone

        text = path.read_text()
        dt_utc = parse_utc_iso(text)
        if dt_utc is None:
            print(f"SKIP {path.name}: could not find a parseable timestamp inside")
            continue

        new_name = new_filename_for(dt_utc, failed=is_old_failed)
        target = JOURNAL / new_name
        if target.exists() and target != path:
            i = 2
            stem = new_name[:-3]
            while (JOURNAL / f"{stem}-{i}.md").exists():
                i += 1
            new_name = f"{stem}-{i}.md"
            target = JOURNAL / new_name

        renames.append((path, target))

    if not renames:
        print("Nothing to migrate — no old-scheme filenames found.")
        return

    for old, new in renames:
        print(f"{old.name}  ->  {new.name}")

    if dry_run:
        print(f"\n(dry run — {len(renames)} file(s) would be renamed, nothing changed)")
        return

    for old, new in renames:
        old.rename(new)
    print(f"\nRenamed {len(renames)} file(s). Remember to 'git add -A' and commit.")


if __name__ == "__main__":
    main()
