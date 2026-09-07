import json
from pathlib import Path
import sys

def main():
    tools_dir = Path(__file__).resolve().parent
    # Candidate search locations: memory/ (parents[2]), memory/core_workspace/ (parents[1]), repo root (parents[2].parent)
    candidate_dirs = [
        tools_dir.parents[2],
        tools_dir.parents[1],
        tools_dir.parents[2].parent,
    ]

    target_files = ["growth_plan.json", "hypotheses.json", "commitments.json", "tool_runs.json"]
    
    found_files = {}
    missing_files = []
    invalid_json = []

    for target in target_files:
        found_path = None
        for cdir in candidate_dirs:
            p = cdir / target
            if p.exists() and p.is_file():
                found_path = p
                break
        
        if found_path is None:
            missing_files.append(target)
        else:
            try:
                with open(found_path, "r", encoding="utf-8") as f:
                    json.load(f)
                found_files[target] = str(found_path)
            except Exception as e:
                invalid_json.append(f"{target}: {str(e)}")

    status = "STRUCTURALLY_COMPLETE" if not missing_files and not invalid_json else "STRUCTURALLY_INVALID"

    output = {
        "status": status,
        "missing_files": missing_files,
        "invalid_json": invalid_json,
        "found_files": found_files
    }

    print(json.dumps(output, indent=2))
    if status != "STRUCTURALLY_COMPLETE":
        sys.exit(1)

if __name__ == "__main__":
    main()
