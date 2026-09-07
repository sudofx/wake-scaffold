import json
import sys
from pathlib import Path

def check_integrity():
    tools_dir = Path(__file__).resolve().parent
    core_workspace = tools_dir.parent
    memory_dir = core_workspace.parent
    repo_root = memory_dir.parent

    targets = {
        "rules_md": memory_dir / "core_identity" / "rules.md",
        "blog_index": memory_dir / "core_persona" / "blog" / "html" / "index.html",
        "memory_index": memory_dir / "core_memories" / "index.md",
        "failure_modes": core_workspace / "failure_modes.md",
        "tool_runs": core_workspace / "tool_runs.json",
        "tools_dir": tools_dir,
    }

    found_required = []
    missing_required = []

    for name, path in targets.items():
        if path.exists():
            found_required.append(f"{name}: {path}")
        else:
            missing_required.append(f"{name}: {path}")

    all_exist = len(missing_required) == 0
    status = "STRUCTURALLY_COMPLETE" if all_exist else "STRUCTURALLY_INVALID"

    output = {
        "status": status,
        "missing_required": missing_required,
        "found_required": found_required,
        "script_location": str(Path(__file__).resolve()),
        "repo_root_resolved": str(repo_root),
        "memory_dir_resolved": str(memory_dir),
        "check_count": len(targets),
        "all_targets_exist": all_exist,
    }

    print(json.dumps(output, indent=2))
    if not all_exist:
        sys.exit(1)

if __name__ == "__main__":
    check_integrity()
