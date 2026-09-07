import os
from pathlib import Path
import json

def main():
    # Target files to find
    targets = {'growth_plan.json', 'hypotheses.json', 'commitments.json', 'tool_runs.json'}
    found = {}
    
    # Resolve the repository root (four levels up from tools directory inside memory/core_workspace/tools/)
    tools_dir = Path(__file__).resolve().parent
    repo_root = tools_dir.parents[3] # tools (0) -> core_workspace (1) -> memory (2) -> repo_root (3)
    
    print(f"Searching from repo root: {repo_root}")
    
    for root, dirs, files in os.walk(repo_root):
        for file in files:
            if file in targets:
                abs_path = Path(root) / file
                found[file] = str(abs_path)
                
    output = {
        "status": "EVIDENCE_AVAILABLE",
        "repo_root": str(repo_root),
        "found": found,
        "missing": list(targets - set(found.keys()))
    }
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
