import json
import os
from pathlib import Path

def validate():
    curr = Path(__file__).resolve().parent
    discovered_root = None
    for p in [curr] + list(curr.parents):
        if (p / "memory").is_dir():
            discovered_root = p
            break
    if not discovered_root:
        return {
            "status": "STRUCTURALLY_INVALID",
            "mechanism": "Repo root containing memory folder not found",
            "cwd": str(Path.cwd())
        }
    checks = {
        "memory_dir": (discovered_root / "memory").is_dir(),
        "core_workspace_dir": (discovered_root / "memory" / "core_workspace").is_dir(),
        "tools_dir": (discovered_root / "memory" / "core_workspace" / "tools").is_dir(),
        "journal_dir": (discovered_root / "memory" / "core_workspace" / "journal").is_dir()
    }
    status = "STRUCTURALLY_COMPLETE" if all(checks.values()) else "STRUCTURALLY_INVALID"
    return {
        "status": status,
        "mechanism": "Parent walk and core directory verification",
        "discovered_root": str(discovered_root),
        "checks": checks
    }

if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
