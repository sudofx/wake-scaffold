#!/usr/bin/env python3
"""Rotate the README comic cover without touching research state or model calls."""

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COVER_PATTERN = re.compile(r"assets/covers/cover-[a-zA-Z0-9_-]+[.]png")


def discover(root=ROOT):
    return sorted((Path(root) / "assets" / "covers").glob("cover-*.png"))


def active(readme, root=ROOT):
    matches = COVER_PATTERN.findall(Path(readme).read_text())
    if len(matches) != 1:
        raise ValueError("README must reference exactly one WAKE Lab Comics cover")
    path = Path(root) / matches[0]
    if not path.is_file():
        raise ValueError("README cover does not exist")
    return path


def choose(options, current, cycle):
    options = sorted(Path(item) for item in options)
    if not options:
        raise ValueError("No WAKE Lab Comics covers found")
    if len(options) == 1:
        return options[0]
    candidate = options[cycle % len(options)]
    if candidate == Path(current):
        candidate = options[(options.index(candidate) + 1) % len(options)]
    return candidate


def rotate(root=ROOT, cycle=0):
    root = Path(root)
    readme = root / "README.md"
    current = active(readme, root)
    selected = choose(discover(root), current, cycle)
    if selected == current:
        return None
    relative = selected.relative_to(root).as_posix()
    content, count = COVER_PATTERN.subn(relative, readme.read_text())
    if count != 1:
        raise ValueError("README cover reference changed unexpectedly")
    readme.write_text(content)
    return relative


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", type=int, required=True)
    args = parser.parse_args()
    changed = rotate(cycle=args.cycle)
    print(changed or "Single cover; nothing to rotate.")
