import os
import json
import pathlib

def get_repo_root():
    # Traverse up from current dir to find identity.md
    curr = pathlib.Path.cwd()
    for _ in range(5):
        if (curr / 'memory/core_identity/identity.md').exists():
            return curr
        curr = curr.parent
    return None

def audit():
    root = get_repo_root()
    if not root:
        return {"status": "ERROR", "message": "Could not find repo root"}
    
    workspace = root / "memory" / "core_workspace"
    results = {"workspace_root": str(workspace), "status": "STRUCTURALLY_COMPLETE", "failures": []}
    
    required_files = ["index.md", "commitments.json", "tool_runs.json"]
    for f in required_files:
        path = workspace / f
        if not path.exists():
            results["failures"].append(f"Missing file: {f}")
            results["status"] = "STRUCTURALLY_INVALID"
    
    return results

if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))