#!/usr/bin/env python3
"""
Validate a proposed memory/core_memories/index.md against ground truth
already sitting elsewhere in the repo, before a human reviews the PR.

This does NOT judge writing quality, tone, or completeness — only
whether specific, checkable claims in the proposal are actually true:

  1. Any growth-plan project ID (g-YYYY-MM-DD-HHMMSS-N) or hypothesis ID
     (h-YYYY-MM-DD-HHMMSS-N) mentioned in index.md, cross-checked against
     its real status in growth_plan.json / hypotheses.json. Catches the
     class of error where a wake claims something is "complete" or
     "confirmed" in prose without it actually being recorded that way.

  2. Any backtick-quoted file path mentioned (e.g. `rules.md`,
     `blog.html`) checked against the actual filesystem, tried against
     several plausible base directories. Catches the exact failure mode
     already observed live in this repo: workspace_integrity_checker.py
     assumed rules.md and blog.html lived at the repo root three wakes
     in a row when they don't.

This is a heuristic safety net, not a replacement for human review. It
can have false positives (e.g. a path mentioned that's intentionally
hypothetical) and should fail the CI check loudly rather than silently
passing on ambiguity — a human reviewing a flagged PR is cheap; an
unflagged wrong claim landing in the one file every future wake trusts
is not.

Run from repo root: python .github/scripts/validate_index_proposal.py
Exits 0 if no hard mismatches found, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "memory"
MEMORIES_DIR = MEMORY / "core_memories"
INDEX_MD = MEMORIES_DIR / "index.md"
GROWTH_PLAN = MEMORIES_DIR / "growth_plan.json"
HYPOTHESES = MEMORIES_DIR / "hypotheses.json"

# Candidate base directories to try when resolving a bare filename
# mentioned in index.md prose (e.g. "rules.md" with no path prefix).
PATH_SEARCH_BASES = [
    ROOT,
    MEMORY,
    MEMORY / "core_identity",
    MEMORY / "core_memories",
    MEMORY / "core_persona" / "blog" / "html",
    MEMORY / "core_workspace",
    MEMORY / "core_workspace" / "tools",
]

ID_RE = re.compile(r"\b([gh]-\d{4}-\d{2}-\d{2}-\d{6}-\d+)\b")
# A conservative set of filename-like tokens inside backticks, e.g.
# `rules.md`, `memory/index.md`, `tools/env_check.py`.
PATH_RE = re.compile(r"`([\w./-]+\.(?:md|html|json|py))`")

GROWTH_STATUSES = ("proposed", "active", "complete")
HYPOTHESIS_STATUSES = ("untested", "confirmed", "refuted", "inconclusive")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"::error::Could not parse {path.relative_to(ROOT)}: {e}")
        sys.exit(1)


def nearby_status(text: str, idx: int, statuses: tuple[str, ...], window: int = 160) -> str | None:
    """Look for a status keyword within `window` chars around position idx."""
    lo, hi = max(0, idx - window), min(len(text), idx + window)
    snippet = text[lo:hi].lower()
    found = [s for s in statuses if re.search(rf"\b{s}\b", snippet)]
    # If more than one status word appears nearby, this is ambiguous —
    # better to flag it for a human than to guess.
    if len(found) == 1:
        return found[0]
    return None


def check_ids(index_text: str, growth: dict, hyps: dict) -> list[str]:
    problems = []
    growth_by_id = {p["id"]: p for p in growth.get("projects", [])}
    hyp_by_id = {h["id"]: h for h in hyps.get("hypotheses", [])}

    for m in ID_RE.finditer(index_text):
        full_id = m.group(1)
        claimed = nearby_status(
            index_text, m.start(),
            GROWTH_STATUSES if full_id.startswith("g-") else HYPOTHESIS_STATUSES,
        )
        if claimed is None:
            continue  # no unambiguous status claim nearby — nothing to check

        if full_id.startswith("g-"):
            record = growth_by_id.get(full_id)
            if record is None:
                problems.append(
                    f"index.md references growth project {full_id!r} which "
                    f"does not exist in growth_plan.json."
                )
            elif record["status"] != claimed:
                problems.append(
                    f"index.md claims {full_id} is {claimed!r}, but "
                    f"growth_plan.json has status {record['status']!r}."
                )
        else:
            record = hyp_by_id.get(full_id)
            if record is None:
                problems.append(
                    f"index.md references hypothesis {full_id!r} which "
                    f"does not exist in hypotheses.json."
                )
            elif record["status"] != claimed:
                problems.append(
                    f"index.md claims {full_id} is {claimed!r}, but "
                    f"hypotheses.json has status {record['status']!r}."
                )
    return problems


def check_paths(index_text: str) -> list[str]:
    warnings = []
    for m in PATH_RE.finditer(index_text):
        raw = m.group(1)
        candidate = Path(raw)
        found = False
        # Try as given (relative to repo root), then against each base dir.
        for base in PATH_SEARCH_BASES:
            if (base / candidate).exists() or (base / candidate.name).exists():
                found = True
                break
        if not found:
            warnings.append(
                f"index.md references `{raw}` — no matching file found at "
                f"repo root, memory/, or common subdirectories. Verify this "
                f"path is real before merging (see: env_check.py and "
                f"workspace_integrity_checker.py both shipped wrong "
                f"hardcoded paths for exactly this reason)."
            )
    return warnings


def main() -> int:
    if not INDEX_MD.exists():
        print("No index.md found — nothing to validate.")
        return 0

    index_text = INDEX_MD.read_text()
    growth = load_json(GROWTH_PLAN)
    hyps = load_json(HYPOTHESES)

    errors = check_ids(index_text, growth, hyps)
    warnings = check_paths(index_text)

    summary_lines = ["# index.md validation report", ""]

    if errors:
        summary_lines.append(f"## ❌ {len(errors)} status mismatch(es) found")
        for e in errors:
            summary_lines.append(f"- {e}")
    else:
        summary_lines.append("## ✅ No status mismatches found")
        summary_lines.append(
            "All growth-project and hypothesis IDs mentioned in index.md "
            "with a nearby status claim match their real status in "
            "growth_plan.json / hypotheses.json."
        )

    summary_lines.append("")

    if warnings:
        summary_lines.append(f"## ⚠️ {len(warnings)} path(s) worth a second look")
        for w in warnings:
            summary_lines.append(f"- {w}")
    else:
        summary_lines.append("## ✅ No suspicious file paths found")

    report = "\n".join(summary_lines)
    print(report)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write(report + "\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
