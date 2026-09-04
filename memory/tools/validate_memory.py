import json
import sys
from pathlib import Path

def validate_workspace():
    tools_dir = Path(__file__).resolve().parent
    workspace_root = tools_dir.parent
    
    memory_dir = workspace_root / "memory"
    if not memory_dir.exists():
        memory_dir = Path.cwd() / "memory"
    
    report = {
        "workspace_root": str(workspace_root),
        "memory_dir": str(memory_dir),
        "checks": {},
        "valid": True
    }
    
    if not memory_dir.exists():
        report["valid"] = False
        report["error"] = f"Memory directory not found at {memory_dir}"
        print(json.dumps(report, indent=2))
        sys.exit(1)
        
    required_files = [
        "identity.md",
        "rules.md",
        "growth_plan.json",
        "hypotheses.json",
        "commitments.json",
        "blog.html"
    ]
    
    for filename in required_files:
        file_path = memory_dir / filename
        exists = file_path.exists()
        file_status = {"exists": exists, "valid_json": None}
        
        if not exists:
            report["valid"] = False
        elif filename.endswith(".json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
                file_status["valid_json"] = True
            except Exception as e:
                file_status["valid_json"] = False
                file_status["json_error"] = str(e)
                report["valid"] = False
                
        report["checks"][filename] = file_status
        
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["valid"] else 1)

if __name__ == "__main__":
    validate_workspace()
