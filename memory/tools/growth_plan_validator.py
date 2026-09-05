import json
import os
import sys

def validate_growth_plan(filepath):
    candidate_paths = [
        filepath,
        os.path.join("..", filepath),
        os.path.join("memory", filepath)
    ]
    target_path = None
    for p in candidate_paths:
        if os.path.exists(p):
            target_path = p
            break
            
    if not target_path:
        return {"valid": False, "error": f"File not found: {filepath}"}
        
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"valid": False, "error": f"JSON parse error: {str(e)}"}
        
    if not isinstance(data, list):
        return {"valid": False, "error": "Root JSON element must be an array of projects."}
        
    required_fields = ["id", "status", "title", "capability", "next_step"]
    errors = []
    counts = {"total": len(data), "active": 0, "complete": 0, "proposed": 0, "blocked": 0}
    
    for idx, proj in enumerate(data):
        if not isinstance(proj, dict):
            errors.append(f"Item [{idx}] is not a JSON object.")
            continue
            
        for f in required_fields:
            if f not in proj or not proj[f]:
                errors.append(f"Item [{idx}] missing required field: '{f}'")
                
        status = proj.get("status")
        if status in counts:
            counts[status] += 1
        else:
            errors.append(f"Item [{idx}] has invalid status: '{status}'")
            
        if status == "complete" and not proj.get("evidence"):
            errors.append(f"Item [{idx}] marked 'complete' but missing 'evidence' string.")
            
    return {
        "valid": len(errors) == 0,
        "path_used": target_path,
        "summary": counts,
        "errors": errors
    }

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "growth_plan.json"
    result = validate_growth_plan(target)
    print(json.dumps(result, indent=2))
