#!/usr/bin/env python3
"""Explicitly install/remove WAKE's cron entry, preserving other scheduled jobs."""

import argparse
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKER = "# wake-managed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--print", action="store_true", dest="preview")
    args = parser.parse_args()
    (ROOT / "data").mkdir(exist_ok=True)
    entry = f"0 */3 * * * {shlex.quote(sys.executable)} {shlex.quote(str(ROOT/'scripts/scheduled_wake.py'))} >> {shlex.quote(str(ROOT/'data/cron.log'))} 2>&1 {MARKER}"
    if args.preview:
        print(entry)
        sys.exit(0)
    previous = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if previous.returncode and "no crontab" not in previous.stderr.lower():
        sys.exit(previous.stderr)
    lines = [line for line in previous.stdout.splitlines() if MARKER not in line]
    if not args.remove:
        lines.append(entry)
    subprocess.run(["crontab", "-"], input="\n".join(lines)+"\n", text=True, check=True)
    print("WAKE schedule removed." if args.remove else "WAKE scheduled every three hours while this computer is awake.")
