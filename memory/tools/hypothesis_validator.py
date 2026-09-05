import sys
import json
import os

def find_hypotheses_file(custom_path=None):
    candidate_paths = []
    if custom_path:
        candidate_paths.append(custom_path)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    defaults = [
        "memory/hypotheses.json",
        "../memory/hypotheses.json",
        "./hypotheses.json",
        os.path.join(script_dir, "../memory/hypotheses.json"),
        os.path.join(script_dir, "hypotheses.json"),
        os.path.join(script_dir, "../../memory/hypotheses.json")
    ]
    
    candidate_paths.extend(defaults)
    
    for path in candidate_paths:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None

def validate_hypotheses(file_path=None):
    resolved_path = find_hypotheses_file(file_path)
    if not resolved_path:
        return {
            "valid": False,
            "error": "File not found among candidate paths."
        }
    
    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            return {"valid": False, "error": "Root JSON must be a list of hypothesis objects."}
        
        errors = []
        required_keys = {"id", "status", "prediction", "test_method"}
        valid_statuses = {"untested", "testing", "confirmed", "refuted", "inconclusive"}
        
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {idx}: Not a JSON object.")
                continue
            missing = required_keys - set(item.keys())
            if missing:
                errors.append(f"Item {idx} (id={item.get('id', 'unknown')}): Missing keys {sorted(list(missing))}")
            if item.get("status") not in valid_statuses:
                errors.append(f"Item {idx} (id={item.get('id', 'unknown')}): Invalid status '{item.get('status')}'")
        
        if errors:
            return {"valid": False, "resolved_path": resolved_path, "errors": errors}
        
        return {
            "valid": True,
            "resolved_path": resolved_path,
            "count": len(data)
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}

if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    res = validate_hypotheses(path_arg)
    print(json.dumps(res, indent=2))
