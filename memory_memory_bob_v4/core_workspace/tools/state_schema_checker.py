import json
import sys
from pathlib import Path

def main():
    tools_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[3]
    
    target_files = [
        "growth_plan.json",
        "hypotheses.json",
        "commitments.json",
        "tool_runs.json"
    ]
    
    found_files = {}
    missing_files = []
    invalid_json = []
    
    for target in target_files:
        matches = list(repo_root.glob(f"**/{target}"))
        if matches:
            matches.sort(key=lambda p: len(p.parts))
            selected = matches[0]
            found_files[target] = str(selected)
            try:
                with open(selected, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                invalid_json.append(f"{target}: {str(e)}")
        else:
            missing_files.append(target)
            
    if not missing_files and not invalid_json:
        status = "STRUCTURALLY_COMPLETE"
        exit_code = 0
    else:
        status = "STRUCTURALLY_INVALID"
        exit_code = 1
        
    output = {
        "status": status,
        "found_files": found_files,
        "missing_files": missing_files,
        "invalid_json": invalid_json,
        "repo_root": str(repo_root)
    }
    
    print(json.dumps(output, indent=2))
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
