import os
import sys
import json
from pathlib import Path

def find_workspace_root():
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    for start in candidates:
        curr = start
        while curr != curr.parent:
            if (curr / "memory").is_dir():
                return curr
            curr = curr.parent
    return Path.cwd()

def validate():
    root = find_workspace_root()
    checks = {
        "memory": root / "memory",
        "core_workspace": root / "memory" / "core_workspace",
        "identity.md": [
            root / "memory" / "core_identity" / "identity.md",
            root / "memory" / "identity.md",
            root / "identity.md"
        ],
        "rules.md": [
            root / "memory" / "core_identity" / "rules.md",
            root / "memory" / "rules.md",
            root / "rules.md"
        ],
        "index.md": [
            root / "memory" / "core_memories" / "index.md",
            root / "memory" / "index.md",
            root / "index.md"
        ]
    }
    
    found = []
    missing = []
    
    for name, path_item in checks.items():
        if isinstance(path_item, list):
            if any(p.exists() for p in path_item):
                found.append(name)
            else:
                missing.append(name)
        else:
            if path_item.exists():
                found.append(name)
            else:
                missing.append(name)
                
    if not missing:
        result = {
            "status": "STRUCTURALLY_COMPLETE",
            "root": str(root),
            "found": found
        }
    else:
        result = {
            "status": "STRUCTURALLY_INVALID",
            "root": str(root),
            "cwd": str(Path.cwd()),
            "found": found,
            "missing": missing
        }
        
    print(json.dumps(result))

if __name__ == '__main__':
    validate()
