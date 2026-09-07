import json
from pathlib import Path
import sys

def check_integrity():
    # Resolve paths
    script_path = Path(__file__).resolve()
    tools_dir = script_path.parent
    core_workspace = tools_dir.parent
    memory_dir = core_workspace.parent
    repo_root = memory_dir.parent

    targets = {
        "rules_md": memory_dir / "core_identity" / "rules.md",
        "blog_index": memory_dir / "core_persona" / "blog" / "html" / "index.html",
        "memory_index": memory_dir / "core_memories" / "index.md"
    }

    missing_required = []
    found_required = []

    for key, path in targets.items():
        if path.exists():
            found_required.append(f"{key}: {path}")
        else:
            missing_required.append(f"{key}: {path}")

    status = "STRUCTURALLY_COMPLETE" if not missing_required else "STRUCTURALLY_INVALID"

    output = {
        "status": status,
        "missing_required": missing_required,
        "found_required": found_required,
        "script_location": str(script_path),
        "repo_root_resolved": str(repo_root)
    }
    
    print(json.dumps(output, indent=2))
    if missing_required:
        sys.exit(1)

if __name__ == '__main__':
    check_integrity()