import sys
import json
from pathlib import Path

def find_root():
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    for c in candidates:
        curr = c
        while curr != curr.parent:
            if (curr / "memory").is_dir():
                return curr
            curr = curr.parent
    return Path.cwd()

def verify():
    root = find_root()
    required_dirs = ["memory", "memory/core_workspace"]
    required_files_any = [
        ["identity.md", "memory/core_identity/identity.md", "memory/identity.md"],
        ["rules.md", "memory/core_rules/rules.md", "memory/rules.md"],
        ["index.md", "memory/core_index/index.md", "memory/index.md"]
    ]
    
    found = []
    missing = []
    
    for d in required_dirs:
        if (root / d).is_dir():
            found.append(d)
        else:
            missing.append(d)
            
    for group in required_files_any:
        found_file = False
        for f in group:
            if (root / f).is_file():
                found.append(f)
                found_file = True
                break
        if not found_file:
            missing.append(group[0])
            
    status = "STRUCTURALLY_COMPLETE" if not missing else "STRUCTURALLY_INVALID"
    result = {
        "status": status,
        "root": str(root),
        "found": found,
        "missing": missing
    }
    print(json.dumps(result))

if __name__ == "__main__":
    verify()
