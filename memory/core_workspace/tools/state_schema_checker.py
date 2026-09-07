import json
import sys
from pathlib import Path

def check_state_schemas():
    tools_dir = Path(__file__).resolve().parent
    workspace_dir = tools_dir.parent
    
    targets = {
        "growth_plan": workspace_dir / "growth_plan.json",
        "hypotheses": workspace_dir / "hypotheses.json",
        "commitments": workspace_dir / "commitments.json",
        "tool_runs": workspace_dir / "tool_runs.json",
    }
    
    missing_files = []
    invalid_json = []
    validated_files = []
    
    for name, path in targets.items():
        if not path.is_file():
            missing_files.append(f"{name}: {path}")
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
                validated_files.append(f"{name}: {path}")
            except Exception as e:
                invalid_json.append(f"{name}: {e}")
                
    status = "STRUCTURALLY_COMPLETE" if not missing_files and not invalid_json else "STRUCTURALLY_INVALID"
    
    out = {
        "status": status,
        "missing_files": missing_files,
        "invalid_json": invalid_json,
        "validated_files": validated_files
    }
    
    print(json.dumps(out, indent=2))
    sys.exit(0 if status == "STRUCTURALLY_COMPLETE" else 1)

if __name__ == "__main__":
    check_state_schemas()
