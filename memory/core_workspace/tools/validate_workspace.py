import os
import json
from pathlib import Path

def inspect_environment():
    cwd = Path.cwd().resolve()
    hierarchy = []
    curr = cwd
    repo_root = None
    for i in range(7):
        try:
            items = os.listdir(curr)
        except Exception as e:
            items = [f"Error: {e}"]
        if ("memory" in items or ".git" in items) and curr != cwd:
            if repo_root is None:
                repo_root = curr
        hierarchy.append({"level": i, "path": str(curr), "items": items[:15]})
        if curr.parent == curr:
            break
        curr = curr.parent
    if repo_root is None:
        repo_root = cwd
    checks = {
        "memory_dir": (repo_root / "memory").exists(),
        "rules_md": (repo_root / "rules.md").exists(),
        "core_workspace_dir": (repo_root / "memory" / "core_workspace").exists(),
        "tools_dir": (repo_root / "memory" / "core_workspace" / "tools").exists()
    }
    status = "STRUCTURALLY_COMPLETE" if all(checks.values()) else "STRUCTURALLY_INVALID"
    print(json.dumps({
        "status": status,
        "mechanism": "Hierarchical directory walk up parent tree",
        "cwd": str(cwd),
        "discovered_root": str(repo_root),
        "checks": checks,
        "hierarchy_sample": hierarchy
    }, indent=2))

if __name__ == "__main__":
    inspect_environment()
