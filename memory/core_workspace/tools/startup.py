import json
import os
from pathlib import Path

def find_workspace_root():
    cwd = Path.cwd().resolve()
    file_path = Path(__file__).resolve()
    
    candidates = [cwd, file_path.parent, file_path.parent.parent]
    
    for candidate in candidates:
        if (candidate / "memory").exists() or (candidate / "index.md").exists():
            return candidate, cwd, file_path
            
    for start in [cwd, file_path.parent]:
        curr = start
        while curr != curr.parent:
            if (curr / "memory").exists() or (curr / "index.md").exists():
                return curr, cwd, file_path
            curr = curr.parent

    return None, cwd, file_path

def main():
    root, cwd, file_path = find_workspace_root()
    
    if root is None:
        print(json.dumps({
            "status": "STRUCTURALLY_INVALID",
            "cwd": str(cwd),
            "file_path": str(file_path),
            "error": "Workspace root not found"
        }))
        return

    required = ["memory", "index.md", "rules.md", "identity.md"]
    found = []
    missing = []
    
    for item in required:
        if (root / item).exists():
            found.append(item)
        else:
            missing.append(item)
            
    status = "STRUCTURALLY_COMPLETE" if not missing else "STRUCTURALLY_INVALID"
    
    print(json.dumps({
        "status": status,
        "root": str(root),
        "cwd": str(cwd),
        "found": found,
        "missing": missing
    }))

if __name__ == "__main__":
    main()
