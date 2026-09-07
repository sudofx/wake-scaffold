#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

def log_failure_mode(category, description):
    tools_dir = Path(__file__).resolve().parent
    core_workspace = tools_dir.parent
    memory_dir = core_workspace.parent
    target_path = memory_dir / "core_identity" / "failure_modes.md"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    header_needed = not target_path.exists() or target_path.stat().st_size == 0

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry_md = f"### [{timestamp}] {category}\n\n**Description:** {description}\n\n---\n\n"

    try:
        with open(target_path, "a", encoding="utf-8") as f:
            if header_needed:
                f.write("# Identity Failure Modes Log\n\n")
            f.write(entry_md)

        out = {
            "status": "SUCCESS",
            "target_path": str(target_path),
            "category": category,
            "bytes_written": len(entry_md)
        }
        print(json.dumps(out, indent=2))
        return 0
    except Exception as e:
        out = {
            "status": "ERROR",
            "error": str(e),
            "target_path": str(target_path)
        }
        print(json.dumps(out, indent=2))
        return 1

if __name__ == "__main__":
    cat = sys.argv[1] if len(sys.argv) > 1 else "Uncategorized Failure"
    desc = sys.argv[2] if len(sys.argv) > 2 else "No description provided."
    sys.exit(log_failure_mode(cat, desc))
