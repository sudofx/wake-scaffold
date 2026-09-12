#!/usr/bin/env python3
"""Opt-in publishing of generated reports to an isolated GitHub Pages branch."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "journal-pages"
sys.path.insert(0, str(ROOT))
from wake.audit import verify_history
from wake.store import canonical


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def publish(directory):
    source = Path(directory).resolve()
    names = ["index.html", "journal.md", "state.json", "events.jsonl", "head.txt"]
    if not all((source / name).is_file() for name in names):
        raise SystemExit("Export the journal first.")
    # Newer exports include human-readable companions. Keep older fixture exports publishable.
    for name in ("state.md", "state.html", "events.md", "events.html"):
        if (source / name).is_file():
            names.append(name)
    if (source / "experiment.json").exists():
        names.append("experiment.json")
    # Fail before remote access if the export mixes generations or was edited.
    reconstructed, head = verify_history(source / "events.jsonl", (source / "head.txt").read_text())
    if canonical(reconstructed) != canonical(json.loads((source / "state.json").read_text())):
        raise SystemExit("Exported state does not match history; export again before publishing.")
    for item in reconstructed.get("notebooks", {}).values():
        names.extend((f"notebooks/{item['id']}.md", f"notebooks/{item['id']}.html"))
    for item in reconstructed.get("posts", {}).values():
        names.extend((f"blog/{item['id']}.md", f"blog/{item['id']}.html"))
    page = (source / "index.html").read_text()
    embedded = json.loads(page.split('<script id="wake-data" type="application/json">', 1)[1].split('</script>', 1)[0])
    if embedded["head"] != head or canonical(embedded["state"]) != canonical(reconstructed):
        raise SystemExit("HTML does not match the verified export; export again before publishing.")
    remote = git("remote", "get-url", "origin").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="wake-publish-") as folder:
        target = Path(folder)
        git("init", "--quiet", cwd=target)
        git("remote", "add", "origin", remote, cwd=target)
        exists = git("ls-remote", "--exit-code", "--heads", "origin", BRANCH, cwd=target, check=False)
        if exists.returncode == 0:
            git("fetch", "--depth=1", "origin", BRANCH, cwd=target)
            git("checkout", "-b", BRANCH, "FETCH_HEAD", cwd=target)
        elif exists.returncode == 2:
            git("checkout", "--orphan", BRANCH, cwd=target)
        else:
            raise SystemExit("Cannot read the publishing branch; check Git authentication.")
        for name in names:
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target / name)
        if "experiment.json" not in names and (target / "experiment.json").exists():
            (target / "experiment.json").unlink()
        (target / ".nojekyll").touch()
        git("add", "--all", cwd=target)
        if git("diff", "--cached", "--quiet", cwd=target, check=False).returncode == 0:
            print("Published journal is already current.")
            return
        git("-c", "user.name=WAKE✳ Journal", "-c", "user.email=wake@localhost",
            "commit", "--quiet", "-m", "Publish verified WAKE✳ journal", cwd=target)
        # No force push. A competing publisher makes this fail safely.
        git("push", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=target)
    print(f"Journal published to {BRANCH}. Select that branch / root in GitHub Pages settings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publish all exported evidence and raw requests to origin/journal-pages.")
    parser.add_argument("--directory", default=str(ROOT / "site"))
    parser.add_argument("--confirm-public", action="store_true", required=True,
                        help="Confirm that the exported journal, evidence and raw requests may be published")
    args = parser.parse_args()
    publish(args.directory)
