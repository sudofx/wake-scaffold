#!/usr/bin/env python3
"""Cron entry point: one call, refresh the journal, retain a consistent backup."""

from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, "-m", "wake", *args], cwd=ROOT).returncode


if __name__ == "__main__":
    run("init")
    status = run("wake")
    report_status = run("export")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_status = run("backup", str(ROOT / "data" / "backups" / f"wake-{stamp}.sqlite3"))
    settings = tomllib.loads((ROOT / "wake.toml").read_text())
    if settings.get("publish_reports") is True and report_status == 0:
        publish_status = subprocess.run([sys.executable, str(ROOT / "scripts/publish.py"), "--confirm-public"], cwd=ROOT).returncode
        status = status or publish_status
    sys.exit(status or report_status or backup_status)
