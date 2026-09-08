import json
import os
from pathlib import Path

def find_workspace_root():
    for start in [Path.cwd(), Path(__file__).resolve().parent]:
        curr = start
        while curr != curr.parent:
            if (curr / "memory").exists():
                return curr
            curr = curr.parent
    return Path.cwd()

def verify():
    root = find_workspace_root()
    memory_dir = root / "memory"
    
    required_dirs = [
        "memory",
        "memory/core_workspace"
    ]
    
    required_files = ["identity.md", "rules.md", "index.md"]
    
    found = []
    missing = []
    
    for d in required_dirs:
        if (root / d).is_dir():
            found.append(d)
        else:
            missing.append(d)
            
    for file_key in required_files:
        matches = list(memory_dir.glob(f"**/{file_key}")) if memory_dir.exists() else []
        if matches:
            rel = matches[0].relative_to(root).as_posix()
            found.append(rel)
        else:
            missing.append(file_key)
                
    status = "STRUCTURALLY_COMPLETE" if not missing else "STRUCTURALLY_INVALID"
    
    res = {
        "status": status,
        "root": str(root),
        "found": sorted(list(set(found))),
        "missing": sorted(list(set(missing)))
    }
    print(json.dumps(res))

if __name__ == "__main__":
    verify()
